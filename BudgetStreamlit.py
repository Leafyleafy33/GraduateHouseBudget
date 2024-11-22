import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import colorsys
import numpy as np

st.set_page_config(
    page_title="Budget Allocation Dashboard",
    page_icon="💰",
    layout="wide",
)

# Load data
file_path = 'budget_output.xlsx'
df = pd.read_excel(file_path)

# Map Subcommittees to Supreme Categories
subcommittee_to_supreme = {
    'Campus Life Committee': 'Campus Life',
    'Events': 'Campus Life',
    'Outreach': 'Campus Life',
    'Outreach Chair Discretionary': 'Campus Life',
    'Finance Committee': 'Finance',
    'Budget': 'Finance',
    'Data': 'Finance',
    'Finance Chair Discretionary': 'Finance',
    'Marketing Committee': 'Marketing & Comm',
    'Marketing & Communications': 'Marketing & Comm',
    'Marketing and Communications': 'Marketing & Comm',
    'Social Media': 'Marketing & Comm',
    'Media Chair Discretionary': 'Marketing & Comm',
    'Leadership Miscellaneous': 'Leadership',
    'Grad House Chair': 'Leadership',
    'Leadership Chair Discretionary': 'Leadership',
    'Administrative Stuff': 'Leadership',
    'Gradhouse Meetings': 'Leadership',
    'Emergency Reserve': 'Emergency Reserve'
}

df['Supreme_Category'] = df['Subcommittee'].map(subcommittee_to_supreme)
df['Supreme_Category'] = df['Supreme_Category'].fillna('Other')

# Compute Remaining_Budget and Percentage_Spent
df['Remaining_Budget'] = df['Budget_Allocation'] - df['Spent_Budget']
df['Percentage_Spent'] = df['Spent_Budget'] / df['Budget_Allocation']
df['Percentage_Spent'] = df['Percentage_Spent'].replace([np.inf, -np.inf, np.nan], 0)
df['Weight'] = df['Spent_Budget'] / df['Spent_Budget'].sum()

# Aggregate data at the Supreme Category level
supreme_totals = df.groupby('Supreme_Category', as_index=False).agg({
    'Budget_Allocation': 'sum',
    'Spent_Budget': 'sum',
    'Remaining_Budget': 'sum'
})
supreme_totals['Percentage_Spent'] = supreme_totals['Spent_Budget'] / supreme_totals['Budget_Allocation']

# Aggregate data at the Subcommittee level
subcommittee_totals = df.groupby(['Supreme_Category', 'Subcommittee'], as_index=False).agg({
    'Budget_Allocation': 'sum',
    'Spent_Budget': 'sum',
    'Remaining_Budget': 'sum'
})
subcommittee_totals['Percentage_Spent'] = subcommittee_totals['Spent_Budget'] / subcommittee_totals['Budget_Allocation']

# Define nickname mapping with additional abbreviations
nickname_mapping = {
    'Marketing & Comm': 'Mkt & Comm',
    'Marketing and Comm': 'Mkt & Comm',
    'Marketing and Communications': 'Mkt & Comm',
    'Marketing & Communications': 'Mkt & Comm',
    'Marketing Committee': 'Mkt Comm.',
    'Leadership Miscellaneous': 'Leadership Misc',
    'Administrative Stuff': 'Admin Stuff',
    'Finance Chair Discretionary': 'Finance Disc.',
    'Outreach Chair Discretionary': 'Outreach Disc.',
    'Media Chair Discretionary': 'Media Disc.',
    'Leadership Chair Discretionary': 'Leadership Disc.',
    'Campus Life Committee': 'Campus Life',
    'Grad House Chair': 'Grad House',
    'Gradhouse Meetings': 'Grad Meetings',
    'Emergency Reserve': 'Emergency Res.',
    'Social Media': 'Social Media',
    'Budget': 'Budget',
    'Data': 'Data',
    'Events': 'Events',
    'Outreach': 'Outreach',
    'Other': 'Other',
    'Leadership': 'Leadership',
    'Finance': 'Finance',
    'Campus Life': 'Campus Life',
    'Total': 'Total'
}

def get_nickname(label):
    return nickname_mapping.get(label, label)

# Function to abbreviate long labels
def abbreviate_label(label, max_length=15):
    return label if len(label) <= max_length else label[:max_length-3] + '...'

# Initialize lists
labels, parents, values, customdata, ids, parent_ids, colors, texts = [], [], [], [], [], [], [], []

# Function to adjust color brightness based on percentage spent
def adjust_color_lightness(hex_color, percentage_spent):
    r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0, min(1, l * (1 - 0.5 * percentage_spent)))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

color_palette = {
    'Mkt & Comm': '#266725',
    'Finance': '#EBBA45',
    'Campus Life': '#007096',
    'Leadership': '#EB2E47',
    'Emergency Res.': '#419E69',
    'Other': '#6EA095',
    'Total': '#AC9155'
}

# Compute total allocated
total_allocated = df['Budget_Allocation'].sum()

# Total node
labels.append(abbreviate_label(get_nickname('Total')))
ids.append('Total')
parents.append('')
parent_ids.append('')
allocated = total_allocated
values.append(allocated)
spent = df['Spent_Budget'].sum()
remaining = df['Remaining_Budget'].sum()
percentage_spent = spent / allocated
customdata.append([spent, remaining, percentage_spent * 100, 'Total'])
colors.append(color_palette['Total'])
percent_of_total = 100.0
texts.append(f"{labels[-1]} Budget:<br>${allocated:,.0f}<br><br>{labels[-1]} Spent:<br>${spent:,.0f}")

# Supreme Category nodes
for idx, row in supreme_totals.iterrows():
    supreme_label_full = row['Supreme_Category']
    supreme_label_short = get_nickname(supreme_label_full)
    supreme_label_abbrev = abbreviate_label(supreme_label_short)
    supreme_id = f"supreme_{supreme_label_full}"
    labels.append(supreme_label_abbrev)
    ids.append(supreme_id)
    parents.append(abbreviate_label(get_nickname('Total')))
    parent_ids.append('Total')
    allocated = row['Budget_Allocation']
    values.append(allocated)
    spent = row['Spent_Budget']
    remaining = row['Remaining_Budget']
    percentage_spent = row['Percentage_Spent']
    customdata.append([spent, remaining, percentage_spent * 100, supreme_label_full])
    base_color = color_palette.get(supreme_label_short, '#cccccc')
    adjusted_color = adjust_color_lightness(base_color, percentage_spent)
    colors.append(adjusted_color)
    percent_of_total = (allocated / total_allocated) * 100
    texts.append(f"{supreme_label_abbrev}<br>{percent_of_total:.1f}%")

# Subcommittee nodes
for idx, row in subcommittee_totals.iterrows():
    subcommittee_label_full = row['Subcommittee']
    subcommittee_label_short = get_nickname(subcommittee_label_full)
    subcommittee_label_abbrev = abbreviate_label(subcommittee_label_short)
    subcommittee_id = f"subcommittee_{subcommittee_label_full}"
    labels.append(subcommittee_label_abbrev)
    ids.append(subcommittee_id)
    parents.append(abbreviate_label(get_nickname(row['Supreme_Category'])))
    parent_ids.append(f"supreme_{row['Supreme_Category']}")
    allocated = row['Budget_Allocation']
    values.append(allocated)
    spent = row['Spent_Budget']
    remaining = row['Remaining_Budget']
    percentage_spent = row['Percentage_Spent']
    customdata.append([spent, remaining, percentage_spent * 100, subcommittee_label_full])
    base_color = color_palette.get(get_nickname(row['Supreme_Category']), '#cccccc')
    adjusted_color = adjust_color_lightness(base_color, percentage_spent)
    colors.append(adjusted_color)
    texts.append(f"{subcommittee_label_abbrev}<br>${allocated:,.0f}")

# Event nodes
for idx, row in df.iterrows():
    event_label_full = row['Event_Name']
    event_label_short = get_nickname(event_label_full)
    event_label_abbrev = abbreviate_label(event_label_short, max_length=12)
    event_id = f"event_{idx}"
    subcommittee_label_full = row['Subcommittee']
    subcommittee_label_short = get_nickname(subcommittee_label_full)
    subcommittee_label_abbrev = abbreviate_label(subcommittee_label_short)
    labels.append(event_label_abbrev)
    ids.append(event_id)
    parents.append(subcommittee_label_abbrev)
    parent_ids.append(f"subcommittee_{subcommittee_label_full}")
    allocated = row['Budget_Allocation']
    values.append(allocated)
    spent = row['Spent_Budget']
    remaining = row['Remaining_Budget']
    percentage_spent = row['Percentage_Spent']
    customdata.append([spent,    remaining, percentage_spent * 100, event_label_full])
    base_color = color_palette.get(get_nickname(row['Supreme_Category']), '#cccccc')
    adjusted_color = adjust_color_lightness(base_color, percentage_spent)
    colors.append(adjusted_color)
    texts.append(f"{event_label_abbrev}<br>${allocated:,.0f}")

# Ensure data alignment
assert len(labels) == len(parents) == len(values) == len(customdata) == len(ids) == len(parent_ids) == len(colors) == len(texts), "Data lists are not aligned."

# Create the sunburst chart with IDs and custom text
fig = go.Figure(go.Sunburst(
    ids=ids,
    labels=labels,
    parents=parent_ids,
    values=values,
    branchvalues='total',
    customdata=customdata,
    text=texts,
    hovertemplate='<b>%{customdata[3]}</b><br>'
                  'Allocated: $%{value:,.2f}<br>'
                  'Spent: $%{customdata[0]:,.2f}<br>'
                  'Remaining: $%{customdata[1]:,.2f}<br>'
                  'Percentage Spent: %{customdata[2]:.2f}%<extra></extra>',
    marker=dict(
        colors=colors,
        line=dict(color='white', width=.5)  # Slightly thicker black lines for clarity
    ),
    maxdepth=3  # Show only first two levels initially
))

# Update layout for better presentation
fig.update_layout(
    # update the size of the chart
    title='',
    font=dict(size=13, family='Open Sans', color='black'),
    margin=dict(t=0, l=0, r=0, b=0),
    paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
    hoverlabel=dict(
        bgcolor="white",
        font_size=14,
        font_family="Open Sans",
        font_color='black'
    ),
    transition=dict(
        duration=200,
        easing='cubic-in-out'
    ),
    sunburstcolorway=[color_palette.get(get_nickname(label), '#cccccc') for label in labels],
    extendsunburstcolors=True
)

# Adjust text settings to ensure labels are displayed with line breaks
fig.update_traces(
    textinfo='text',
    texttemplate='%{text}',
    insidetextorientation='radial',
    textfont=dict(size=12, family='Open Sans', color='white')
)

header_color = "#F9DCDE"  # Light pink for header to contrast with dark background
subheader_color = "#BFF3FD"  # Light blue for subheader text
main_text_color = "#AC9155"  # Texas State Gold for main text
table_header_bg = "#6EA095"  # Glass-Bottom Boat color for table headers
table_text_color = "#FFFFFF"  # White for table text for readability
table_bg_color = "#501214"  # Texas State Maroon for table background

# Streamlit Page Layout with Color Themes
st.markdown(
    f"""
    <h1 style="text-align: center; color: {header_color}; font-size: 28px; font-weight: bold;">
        Comprehensive Budget Allocation and Spending Overview
    </h1>
    <h3 style="text-align: center; color: {subheader_color}; font-size: 18px;">
        Total Budget: ${df['Budget_Allocation'].sum():,.0f}
    </h3>
    """,
    unsafe_allow_html=True
)

# Summary stats
# Budget summary styling
total_budget = df['Budget_Allocation'].sum()
total_spent = df['Spent_Budget'].sum()
total_remaining = total_budget - total_spent
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-evenly; color: {main_text_color}; font-size: 16px;">
        <span><strong>Spent:</strong> ${total_spent:,.0f}</span>
        <span><strong>Remaining:</strong> ${total_remaining:,.0f}</span>
    </div>
    """,
    unsafe_allow_html=True
)

# Adjust Streamlit Layout
col1, col2 = st.columns([1, 1])  # Adjusted to make the chart smaller

# weight is the percentage of the total budget allocated to each event if not zero, else 0
df['Weight'] = df['Budget_Allocation'] / df['Budget_Allocation'].sum()
df['Weight'] = df['Weight'].replace([np.inf, -np.inf, np.nan], 0)
# Budget Table with Correct Weights

# Budget Table with Correct Weights from Dataset and Custom Styling
with col1:
    st.markdown(
    f"""
    <h2 style="text-align: center; color: {header_color};">Detailed Budget Breakdown</h2>
    """,
    unsafe_allow_html=True
    )


    # Apply table styling using CSS
    st.markdown(
        f"""
        <style>
            .stDataFrame {{
                background-color: {table_bg_color};
                color: {table_text_color};
                font-size: 14px;
            }}
            .stDataFrame tbody tr:hover {{
                background-color: {table_header_bg};
            }}
            .stDataFrame th {{
                background-color: {table_header_bg};
                color: {table_text_color};
                font-weight: bold;
            }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # Prepare the dataframe
    table_df = df[['Event_Name', 'Category', 'Budget_Allocation', 'Spent_Budget', 'Weight']].rename(columns={
        'Event_Name': 'Event',
        'Budget_Allocation': 'Budget',
        'Spent_Budget': 'Spent',
        'Weight': 'Weight (%)',
    })
    table_df = table_df[['Event', 'Category', 'Budget', 'Spent', 'Weight (%)']]  # Rearranged columns

    # Apply pandas Styler
    styled_df = table_df.style.format({
        'Budget': '${:,.2f}',
        'Spent': '${:,.2f}',
        'Weight (%)': '{:.2%}',
    })

    # Display the dataframe
    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=None)


# Display Sunburst Chart
with col2:
    st.markdown(
        f"""
        <h2 style="text-align: center; color: {header_color};">Visual Budget Overview</h2>
        """,
        unsafe_allow_html=True
    )
    st.plotly_chart(fig, use_container_width=True)

