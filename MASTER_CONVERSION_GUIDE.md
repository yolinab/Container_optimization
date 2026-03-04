# Master Guide: Converting Local Python/CPMPy Software to Web Application

## Overview

You have a local Python application using CPMPy for 1D box packing optimization. This guide explains exactly how to restructure it for web deployment via Streamlit on Azure App Service.

---

## PART 1: Understanding the Architecture Change

### Before (Local Software)
```
┌─────────────────────────────────────────┐
│           Your Computer                 │
│  ┌─────────────────────────────────┐   │
│  │  Python Script                   │   │
│  │  ├── Read Excel file from disk   │   │
│  │  ├── Run CPMPy solver            │   │
│  │  └── Save results to disk        │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### After (Web Application)
```
┌──────────────────┐         ┌─────────────────────────────────┐
│  User's Browser  │ ◄─────► │  Azure App Service              │
│  (Any computer)  │   HTTP  │  ┌─────────────────────────┐   │
│                  │         │  │  Streamlit (Web UI)      │   │
│  - Upload Excel  │         │  │  ├── Receive upload      │   │
│  - See results   │         │  │  ├── Call your solver    │   │
│  - Download CSV  │         │  │  └── Return results      │   │
└──────────────────┘         │  └─────────────────────────┘   │
                             │  ┌─────────────────────────┐   │
                             │  │  Your Solver (CPMPy)     │   │
                             │  │  - Unchanged logic!      │   │
                             │  └─────────────────────────┘   │
                             └─────────────────────────────────┘
```

**Key insight:** Your solver logic stays almost identical. You're just adding a web interface layer on top.

---

## PART 2: Code Structure Transformation

### Your Current Code Structure (Probably)
```python
# main.py or similar - Your current local software

import pandas as pd
from cpmpy import *

# 1. HARDCODED FILE PATH
df = pd.read_excel("C:/Users/YourName/data/items.xlsx")

# 2. SOLVER LOGIC (this is the good part - keep it!)
def solve_packing(items, capacity):
    n = len(items)
    box_assignment = intvar(0, n-1, shape=n)
    model = Model()
    # ... your constraints ...
    model.minimize(...)
    model.solve()
    return results

# 3. HARDCODED OUTPUT
results.to_excel("C:/Users/YourName/output/results.xlsx")
print("Done!")
```

### Target Code Structure (Web Application)
```
box-packing-tool/
│
├── app.py              # NEW: Web interface (Streamlit)
│                       # Handles: file upload, user input, display results
│
├── solver.py           # ADAPTED: Your existing solver logic
│                       # Changed: Takes parameters, returns data (no file I/O)
│
├── requirements.txt    # NEW: Python dependencies for deployment
│
└── startup.sh          # NEW: Azure startup command (1 line)
```

---

## PART 3: Step-by-Step Code Changes

### Step 1: Extract Your Solver Logic into a Clean Function

**BEFORE (mixed file I/O and logic):**
```python
# Everything in one script
df = pd.read_excel("items.xlsx")  # File I/O mixed in
items = df['size'].tolist()
capacity = 100  # Hardcoded

# Solver logic
box_assignment = intvar(...)
model = Model()
# ... constraints ...
model.solve()

# Output mixed in
results.to_excel("output.xlsx")
```

**AFTER (clean separation):**
```python
# solver.py - ONLY the solver logic, no file I/O

from cpmpy import *
import numpy as np

def solve_box_packing(item_sizes: list, item_ids: list, box_capacity: int) -> dict:
    """
    Pure solver function - no file reading/writing.
    
    Args:
        item_sizes: List of item sizes (numbers)
        item_ids: List of item identifiers (strings or numbers)
        box_capacity: Maximum capacity per box
    
    Returns:
        Dictionary with solution details
    """
    n_items = len(item_sizes)
    sizes = np.array(item_sizes)
    
    # ========================================
    # YOUR EXISTING CPMPY LOGIC GOES HERE
    # ========================================
    
    # Decision variables
    max_boxes = n_items  # Upper bound
    box_assignment = intvar(0, max_boxes - 1, shape=n_items, name="box")
    box_used = boolvar(shape=max_boxes, name="used")
    num_boxes_used = intvar(0, max_boxes, name="num_boxes")
    
    model = Model()
    
    # Capacity constraints
    for b in range(max_boxes):
        items_in_box = [sizes[i] * (box_assignment[i] == b) for i in range(n_items)]
        model += sum(items_in_box) <= box_capacity
    
    # Link box_used to assignments
    for b in range(max_boxes):
        model += box_used[b] == any(box_assignment[i] == b for i in range(n_items))
    
    # Count boxes
    model += num_boxes_used == sum(box_used)
    
    # Symmetry breaking
    for b in range(max_boxes - 1):
        model += box_used[b + 1] <= box_used[b]
    
    # Objective
    model.minimize(num_boxes_used)
    
    # ========================================
    # END OF YOUR CPMPY LOGIC
    # ========================================
    
    # Solve
    if model.solve():
        # Build result dictionary (for web interface to display)
        assignments = []
        boxes = {}
        
        for i in range(n_items):
            box_id = int(box_assignment[i].value())
            assignments.append({
                'item_id': item_ids[i],
                'item_size': int(sizes[i]),
                'box_id': box_id + 1
            })
            
            if box_id not in boxes:
                boxes[box_id] = []
            boxes[box_id].append({'item_id': item_ids[i], 'size': int(sizes[i])})
        
        return {
            'status': 'optimal',
            'num_boxes': int(num_boxes_used.value()),
            'assignments': assignments,
            'boxes': {k+1: v for k, v in boxes.items()},
            'avg_utilization': calculate_utilization(boxes, box_capacity)
        }
    else:
        return {
            'status': 'infeasible',
            'message': 'No solution found',
            'num_boxes': 0,
            'assignments': [],
            'boxes': {}
        }

def calculate_utilization(boxes, capacity):
    if not boxes:
        return 0
    total = sum(sum(item['size'] for item in items) / capacity for items in boxes.values())
    return total / len(boxes)
```

### Step 2: Create the Web Interface

```python
# app.py - Web interface using Streamlit

import streamlit as st
import pandas as pd
import io
from solver import solve_box_packing  # Import your solver

# Page setup
st.set_page_config(page_title="Box Packing Optimizer", page_icon="📦")
st.title("📦 Box Packing Optimizer")

# FILE UPLOAD (replaces: pd.read_excel("hardcoded_path.xlsx"))
uploaded_file = st.file_uploader("Upload your Excel file", type=['xlsx', 'csv'])

if uploaded_file:
    # Read uploaded file into DataFrame
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Show preview
    st.subheader("Data Preview")
    st.dataframe(df)
    
    # USER INPUT (replaces: hardcoded values)
    size_column = st.selectbox("Select size column", df.columns)
    box_capacity = st.number_input("Box capacity", value=100, min_value=1)
    
    # SOLVE BUTTON
    if st.button("Optimize"):
        # Extract data from DataFrame
        sizes = df[size_column].tolist()
        ids = df.index.tolist()  # Or use another column
        
        # Call your solver
        result = solve_box_packing(sizes, ids, box_capacity)
        
        if result['status'] == 'optimal':
            st.success(f"Solution found! {result['num_boxes']} boxes needed.")
            
            # Display results
            result_df = pd.DataFrame(result['assignments'])
            st.dataframe(result_df)
            
            # DOWNLOAD BUTTON (replaces: results.to_excel("output.xlsx"))
            csv = result_df.to_csv(index=False)
            st.download_button(
                "Download Results",
                csv,
                "packing_results.csv",
                "text/csv"
            )
        else:
            st.error("No solution found")
```

---

## PART 4: What Changes, What Stays the Same

### ✅ KEEP UNCHANGED
- All your CPMPy constraint logic
- Your optimization model
- The mathematical formulation
- Any helper functions for the solver

### 🔄 MODIFY
- **Input:** Change from `pd.read_excel("path")` → function parameter
- **Output:** Change from `df.to_excel("path")` → return dictionary
- **Configuration:** Change from hardcoded values → function parameters

### ➕ ADD NEW
- `app.py` - Streamlit web interface
- `requirements.txt` - dependencies list
- `startup.sh` - Azure startup command

---

## PART 5: Handling Common Patterns

### Pattern A: You have multiple input files
**Before:**
```python
orders = pd.read_excel("orders.xlsx")
inventory = pd.read_excel("inventory.xlsx")
```

**After (in app.py):**
```python
orders_file = st.file_uploader("Upload Orders", type=['xlsx'])
inventory_file = st.file_uploader("Upload Inventory", type=['xlsx'])

if orders_file and inventory_file:
    orders = pd.read_excel(orders_file)
    inventory = pd.read_excel(inventory_file)
    # ... continue
```

### Pattern B: You have configuration settings
**Before:**
```python
# Hardcoded at top of file
MAX_WEIGHT = 1000
PRIORITIES = {'urgent': 3, 'normal': 1}
SOLVER_TIMEOUT = 60
```

**After (in app.py):**
```python
st.sidebar.header("Settings")
max_weight = st.sidebar.number_input("Max weight", value=1000)
solver_timeout = st.sidebar.slider("Solver timeout (sec)", 10, 300, 60)
```

### Pattern C: You print progress/debug info
**Before:**
```python
print("Loading data...")
print(f"Found {len(items)} items")
print("Solving...")
print("Done!")
```

**After:**
```python
st.write("Loading data...")
st.write(f"Found {len(items)} items")

with st.spinner("Solving..."):
    result = solve(...)

st.success("Done!")
```

### Pattern D: You have error handling
**Before:**
```python
try:
    result = solve(...)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
```

**After:**
```python
try:
    result = solve(...)
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()  # Stops execution, keeps UI responsive
```

---

## PART 6: Dependencies (requirements.txt)

List all packages your solver uses:

```
# Web framework
streamlit>=1.28.0

# Data handling
pandas>=2.0.0
numpy>=1.24.0
openpyxl>=3.1.0      # For Excel reading
xlrd>=2.0.0          # For older Excel formats

# Your solver
cpmpy>=0.9.0
ortools>=9.7         # Or whichever solver backend you use

# Add any other packages your code imports:
# scipy>=1.10.0
# networkx>=3.0
# etc.
```

---

## PART 7: Startup Configuration (startup.sh)

```bash
#!/bin/bash
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
```

---

## PART 8: Testing Locally Before Deployment

```bash
# 1. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run locally
streamlit run app.py

# 4. Open browser to http://localhost:8501
# 5. Test with your Excel files
```

---

## PART 9: Deployment Checklist

Before deploying, verify:

- [ ] `solver.py` has NO hardcoded file paths
- [ ] `solver.py` function takes parameters and returns data
- [ ] `app.py` handles file upload via `st.file_uploader()`
- [ ] `app.py` provides download via `st.download_button()`
- [ ] `requirements.txt` lists ALL your dependencies
- [ ] Local test works with `streamlit run app.py`
- [ ] No sensitive data/credentials in code

---

## PART 10: Quick Reference - Streamlit Equivalents

| Local Python | Streamlit Web |
|--------------|---------------|
| `input("Enter value: ")` | `st.text_input("Enter value")` |
| `print("Message")` | `st.write("Message")` |
| `pd.read_excel("file.xlsx")` | `st.file_uploader()` → `pd.read_excel()` |
| `df.to_excel("output.xlsx")` | `st.download_button()` |
| `print(f"Result: {x}")` | `st.metric("Result", x)` |
| `if condition: print("OK")` | `if condition: st.success("OK")` |
| `try/except` with `sys.exit()` | `try/except` with `st.error()` |

---

## Summary: The 3 Things You Actually Need to Do

1. **Extract** your solver logic into a function that takes parameters and returns a dictionary
2. **Create** `app.py` with Streamlit file upload and result display  
3. **List** your dependencies in `requirements.txt`

That's it. Your core optimization logic stays the same.
