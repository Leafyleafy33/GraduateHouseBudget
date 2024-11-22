import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import random
import warnings

# =========================
# Suppress Specific Warnings
# =========================
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)

# =========================
# User Inputs
# =========================
FILE_PATH = 'budget_input.xlsx'
OUTPUT_FILE = 'budget_output.xlsx'

# Initial Budget Configuration
ORIGINAL_BUDGET = 2500.00
TOTAL_BUDGET = ORIGINAL_BUDGET

# Emergency Reserve Configuration
EMERGENCY_RESERVE_PERCENT = 0.05

# Discretionary Allocations
DISCRETIONARY_ALLOCATIONS = {
    'Finance Chair Discretionary': 50,
    'Outreach Chair Discretionary': 100,
    'Media Chair Discretionary': 50,
    'Leadership Chair Discretionary': 50
}

# Core Objectives and Category Base Weights
CORE_OBJECTIVES = {'advocacy': 0.05, 'engagement': 0.65, 'visibility': 0.20, 'operational': 0.10}
CATEGORY_BASE_WEIGHTS = {
    'events': {'engagement': 0.9, 'visibility': 0.1},
    'coffee chat connect': {'engagement': 0.4, 'visibility': 0.3, 'advocacy': 0.2, 'operational': 0.1},
    'gradhouse meetings meetups': {'engagement': 0.2, 'advocacy': 0.6, 'visibility': 0.15, 'operational': 0.05},
    'administrative stuff': {'operational': 1.0},
    'social media': {'visibility': 0.6, 'engagement': 0.4},
    'budget': {'operational': 1.0},
    'data': {'operational': 0.5, 'advocacy': 0.3, 'visibility': 0.2},
    'outreach': {'visibility': 0.5, 'engagement': 0.3, 'advocacy': 0.2},
    'marketing': {'visibility': 0.5, 'engagement': 0.5}
}

# Event Themes for Random Naming
EVENT_THEMES = [
    "Campus Networking Night*", "Research Roundtable*", "Graduate Workshop*", 
    "Academic Mixer*", "Student-Faculty Mixer*", "Career Advancement Session*", 
    "Alumni Networking*", "Panel Discussion*", "Community Service Day*", 
    "Tech Talk*", "Leadership Seminar*", "Skills Development Workshop*", 
    "Funding 101*", "Project Showcase*"
]

# =========================
# Utility Functions
# =========================
def load_sheet(file_path, sheet_index, skip_rows, column_names):
    """
    Load an Excel sheet into a DataFrame.
    """
    df = pd.read_excel(file_path, sheet_name=sheet_index, skiprows=skip_rows)
    df.columns = column_names
    return df.dropna(subset=column_names[:2]).reset_index(drop=True)

def calculate_skewed_weights(objectives, base_weights, skew=3):
    """
    Calculate skewed weights based on core objectives and category base weights.
    """
    core_df = pd.DataFrame.from_dict(objectives, orient='index', columns=['weight'])
    category_df = pd.DataFrame.from_dict(base_weights, orient='index').fillna(0)
    weighted_scores = category_df.mul(core_df['weight'] ** skew, axis=1).sum(axis=1)
    return (weighted_scores / weighted_scores.sum()).to_dict()

def rebalance_budget(df, total_budget, skewed_weights):
    """
    Rebalance the budget by locking allocations for closed or overspent events
    before distributing the remaining budget to active events.
    """
    # Identify closed or overspent events
    closed_or_overspent = (df['Status'] == 'Closed') | (df['Spent_Budget'] > df['Budget_Allocation'])
    
    # Lock allocations for these events
    df.loc[closed_or_overspent, 'Budget_Allocation'] = df.loc[closed_or_overspent, 'Spent_Budget']
    
    # Calculate total spent
    total_spent = df['Spent_Budget'].sum()
    remaining_budget = total_budget - total_spent
    
    # Handle active events
    open_events_mask = (~closed_or_overspent) & (df['Spent_Budget'] <= df['Budget_Allocation'])
    open_events = df.loc[open_events_mask].copy()
    
    if remaining_budget > 0 and not open_events.empty:
        # Assign weights based on skewed_weights
        open_events['Weight'] = open_events['Event_Name'].map(skewed_weights)
        total_weight = open_events['Weight'].sum()
        open_events['Weight'] = (open_events['Weight'] / total_weight).round(2)
        
        # Allocate remaining budget based on weights
        open_events['Budget_Allocation'] = (open_events['Weight'] * remaining_budget).round(2)
        
        # Update the main DataFrame
        df.loc[open_events_mask, 'Weight'] = open_events['Weight']
        df.loc[open_events_mask, 'Budget_Allocation'] = open_events['Budget_Allocation']
    
    return df

def adjust_rounding(df, target_total, budget_column="Budget_Allocation"):
    """
    Adjust the budget allocations to ensure the total matches the target by correcting rounding errors.
    """
    current_total = df[budget_column].sum()
    difference = round(target_total - current_total, 2)
    if difference != 0:
        idx = df[budget_column].idxmax()
        df.at[idx, budget_column] += difference
    return df

def generate_event_dates(start_date, end_date, num_events, target_weekday):
    """
    Generate a list of event dates on a specified weekday within a date range.
    """
    interval = (end_date - start_date).days // max(num_events - 1, 1)
    dates = []
    for i in range(num_events):
        base_date = start_date + timedelta(days=i * interval)
        days_ahead = (target_weekday - base_date.weekday() + 7) % 7
        event_date = base_date + timedelta(days=days_ahead)
        dates.append(event_date)
    return dates

def assign_weights(new_df, new_events_df, skewed_weights):
    """
    Assign weights and budget allocations to new events.
    """
    total_budget = new_df.loc[new_df['Event_Name'] == 'events', 'Budget_Allocation'].sum()
    if total_budget <= 0:
        raise ValueError("Total budget for 'events' is zero or negative.")
    
    weights = np.exp(np.linspace(0, 1, len(new_events_df)))
    weights /= weights.sum()
    
    new_events_df['Weight'] = weights
    new_events_df['Budget_Allocation'] = (new_events_df['Weight'] * total_budget).round(2)
    
    return new_events_df

def categorize_event(name):
    """
    Categorize events based on their names.
    """
    name_lower = name.lower()
    if 'discretionary' in name_lower:
        return 'Discretionary'
    if 'emergency reserve' in name_lower:
        return 'Emergency Reserve'
    if 'administrative' in name_lower or 'gradhouse' in name_lower:
        return 'Administrative'
    if any(keyword in name_lower for keyword in ['outreach', 'marketing', 'data', 'budget', 'social media']):
        return 'Committee'
    if '*' in name:
        return 'Fake Event'
    return 'General Event'

# =========================
# Main Function
# =========================
def main():
    global TOTAL_BUDGET  # To modify the global TOTAL_BUDGET
    
    # =====================
    # Load Data
    # =====================
    columns = {
        'accounts': ["Event_Name", "Subcommittee", "Budget_Allocation", "Spent_Budget", "Status"],
        'expenses': ["Expense_ID", "Date", "Subcommittee", "Description", "Amount", "Related_Event", "Notes"]
    }
    
    accounts_df = load_sheet(FILE_PATH, 0, 3, columns['accounts'])
    expenses_df = load_sheet(FILE_PATH, 1, 3, columns['expenses'])
    
    # Display loaded DataFrames (Optional: Remove or comment out in production)
    # print("Accounts DataFrame:")
    # print(accounts_df)
    # print("\nExpenses DataFrame:")
    # print(expenses_df)
    
    # =====================
    # Initialize Budget Variables
    # =====================
    # Preallocate discretionary budgets
    preallocations = sum(DISCRETIONARY_ALLOCATIONS.values())
    TOTAL_BUDGET -= preallocations
    
    # Allocate Emergency Reserve
    EMERGENCY_RESERVE = TOTAL_BUDGET * EMERGENCY_RESERVE_PERCENT
    TOTAL_BUDGET -= EMERGENCY_RESERVE
    
    # print(f'\nTotal Budget After Preallocations: {TOTAL_BUDGET:.2f}')
    
    # Keep a copy of the original accounts DataFrame
    original_accounts_df = accounts_df.copy()
    
    # =====================
    # Event Processing and Filtering
    # =====================
    accounts_df['Event_Name'] = accounts_df['Event_Name'].str.lower()
    event_names = accounts_df.loc[~accounts_df['Event_Name'].str.contains('discretionary'), 'Event_Name'].unique()
    
    # =====================
    # Calculate Skewed Weights
    # =====================
    skewed_weights = calculate_skewed_weights(CORE_OBJECTIVES, CATEGORY_BASE_WEIGHTS)
    
    # =====================
    # Map Expenses to Events
    # =====================
    accounts_df = accounts_df[accounts_df['Event_Name'].isin(event_names)].reset_index(drop=True)
    expenses_dict = {event: expenses_df[expenses_df['Related_Event'].str.lower() == event] for event in event_names}
    total_expenses = {event: expenses['Amount'].sum() for event, expenses in expenses_dict.items()}
    
    # =====================
    # Assign Weights and Budget Allocations
    # =====================
    accounts_df['Weight'] = accounts_df['Event_Name'].map(skewed_weights)
    accounts_df['Spent_Budget'] = accounts_df['Event_Name'].map(total_expenses).fillna(0)
    accounts_df['Budget_Allocation'] = (accounts_df['Weight'] * TOTAL_BUDGET).round(2)
    
    # =====================
    # Rebalance Budget Based on Expenses and Status
    # =====================
    new_df = rebalance_budget(accounts_df, TOTAL_BUDGET, skewed_weights)
    
    # =====================
    # Adjust for Rounding Errors
    # =====================
    new_df = adjust_rounding(new_df, new_df['Budget_Allocation'].sum(), "Budget_Allocation")
    new_df['Weight'] = (new_df['Budget_Allocation'] / ORIGINAL_BUDGET).round(4)
    
    # print("\nRebalanced Budget DataFrame:")
    # print(new_df)
    
    # =====================
    # Handle Discretionary Events
    # =====================
    discretionary_events = original_accounts_df[
        original_accounts_df['Event_Name'].str.contains('discretionary', case=False)
    ].copy()
    
    if not discretionary_events.empty:
        # Assign Budget Allocation based on discretionary mapping and set Weight to 0
        discretionary_events['Budget_Allocation'] = discretionary_events['Event_Name'].map(DISCRETIONARY_ALLOCATIONS)
        discretionary_events['Weight'] = 0
        
        # Ensure 'Spent_Budget' column exists, set to 0 for discretionary events
        if 'Spent_Budget' not in discretionary_events.columns:
            discretionary_events['Spent_Budget'] = 0
        
        # Create Emergency Reserve Entry
        emergency_reserve_data = {
            'Event_Name': 'Emergency Reserve',
            'Subcommittee': 'Leadership Miscellaneous',
            'Budget_Allocation': EMERGENCY_RESERVE,
            'Spent_Budget': 0,
            'Status': 'Closed',
            'Weight': 0
        }
        emergency_reserve_df = pd.DataFrame([emergency_reserve_data])
        
        # Combine Discretionary Events with Emergency Reserve
        discretionary_events = pd.concat([discretionary_events, emergency_reserve_df], ignore_index=True)
        
        # =====================
        # Combine with Main DataFrame
        # =====================
        new_df = pd.concat([new_df, discretionary_events], ignore_index=True)
    else:
        # If no discretionary events, still add Emergency Reserve
        emergency_reserve_data = {
            'Event_Name': 'Emergency Reserve',
            'Subcommittee': 'Leadership Miscellaneous',
            'Budget_Allocation': EMERGENCY_RESERVE,
            'Spent_Budget': 0,
            'Status': 'Closed',
            'Weight': 0
        }
        emergency_reserve_df = pd.DataFrame([emergency_reserve_data])
        new_df = pd.concat([new_df, emergency_reserve_df], ignore_index=True)
    
    # Recalculate Weights Based on ORIGINAL_BUDGET
    new_df['Weight'] = (new_df['Budget_Allocation'] / ORIGINAL_BUDGET).round(4)
    
    # Adjust for Rounding Errors Again
    new_df = adjust_rounding(new_df, new_df['Budget_Allocation'].sum(), "Budget_Allocation")
    new_df['Weight'] = (new_df['Budget_Allocation'] / ORIGINAL_BUDGET).round(4)
    
    # print("\nAfter Adding Discretionary and Emergency Reserve:")
    # print(new_df)
    
    # =====================
    # Generate New Events
    # =====================
    today = datetime.today().date()
    if today.month < 7:
        start_date = datetime(today.year, 8, 23).date()
        end_date = datetime(today.year, 12, 10).date()
    else:
        start_date = datetime(today.year, 1, 23).date()
        end_date = datetime(today.year, 5, 10).date()
    
    # Generate 10 event dates for Tuesday (weekday = 1)
    event_dates = generate_event_dates(start_date, end_date, 10, 1)
    
    # Define columns for the new events DataFrame
    columns_new_events = new_df.columns.tolist()
    
    # Create new events DataFrame
    new_events_df = pd.DataFrame([
        [f'Event {i + 1}', 'Events', 0, 0, 'Active', 0]
        for i in range(len(event_dates))
    ], columns=columns_new_events)
    
    # Assign Dates and Status
    new_events_df['Status'] = ['Active' if date > today else 'Closed' for date in event_dates]
    
    # Filter only active events
    new_events_df = new_events_df[new_events_df['Status'] == 'Active'].copy()
    
    # Assign Weights and Budget Allocations to New Events
    if not new_events_df.empty:
        new_events_df = assign_weights(new_df, new_events_df, skewed_weights)
        # print("\nNew Active Events:")
        # print(new_events_df)
        
        # =====================
        # Integrate New Events into Main DataFrame
        # =====================
        new_df = pd.concat([new_df, new_events_df], ignore_index=True)
        new_df = new_df[new_df['Event_Name'].str.lower() != 'events'].reset_index(drop=True)
    else:
        # print("\nNo new active events to add.")
        pass
    
    # Recalculate Weights Based on ORIGINAL_BUDGET
    new_df['Weight'] = (new_df['Budget_Allocation'] / ORIGINAL_BUDGET).round(4)
    
    # Adjust for Rounding Errors Once More
    new_df = adjust_rounding(new_df, new_df['Budget_Allocation'].sum(), "Budget_Allocation")
    new_df['Weight'] = (new_df['Budget_Allocation'] / ORIGINAL_BUDGET).round(4)
    
    # =====================
    # Replace 'Event #' with Random Names from EVENT_THEMES
    # =====================
    new_df['Event_Name'] = new_df['Event_Name'].apply(
        lambda x: random.choice(EVENT_THEMES) if x.startswith('Event') else x
    )
    
    # =====================
    # Categorize Events
    # =====================
    new_df['Category'] = new_df['Event_Name'].apply(categorize_event)
    
    # Define Category Order for Sorting
    category_order = ['Emergency Reserve', 'Discretionary', 'Administrative', 'Fake Event', 'Committee', 'General Event']
    new_df['Category'] = pd.Categorical(new_df['Category'], categories=category_order, ordered=True)
    
    # =====================
    # Sort the DataFrame
    # =====================
    sorted_df = new_df.sort_values(
        ['Category', 'Status', 'Subcommittee', 'Budget_Allocation'],
        ascending=[True, True, True, False]
    ).reset_index(drop=True)
    
    # Final Sanity Check to Ensure Total Allocation and Weight
    sorted_df = adjust_rounding(sorted_df, sorted_df['Budget_Allocation'].sum(), "Budget_Allocation").round(2)
    sorted_df['Weight'] = (sorted_df['Budget_Allocation'] / ORIGINAL_BUDGET).round(2)
    
    # =====================
    # Display Final DataFrame
    # =====================
    # print("\nFinal Sorted Budget Allocation:")
    # display(sorted_df)
    # 
    # print(f'\nTotal Budget Allocation: {sorted_df["Budget_Allocation"].sum():.2f}')
    # print(f'Total Weight: {sorted_df["Weight"].sum():.4f}')
    
    # =====================
    # Save to Excel
    # =====================
    sorted_df.to_excel(OUTPUT_FILE, index=False)
    # print(f'\nBudget allocation saved to {OUTPUT_FILE}')

# =========================
# Execute Main Function
# =========================
if __name__ == "__main__":
    main()
