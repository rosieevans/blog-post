""" athletics.py                                          yyyy-mm-dd:2025-04-09
---|----1----|----2----|----3----|----4----|----5----|----6----|----7----|----8

  This file examines athletics world records for both men and women.  
    It does so by using the data from Wikipedia:
       
  Wikipedia contributors. "List of world records in athletics." Wikipedia.
    https://en.wikipedia.org/wiki/List_of_world_records_in_athletics.

  The data is firstly webscraped from the above link, and saved as a csv.
    This is then read in directly with pd.read_csv().
    Full details related to the replication of this file can be found in the 
    README code in the top level of this directory.

  Contact: mailto:rje215@exeter.ac.uk
"""
#------------------------------------------------------------------------------
#--- (0) Imports and directory locations
#------------------------------------------------------------------------------

import os

# Had some issues detecting filepaths, so used this method instead of the typical one shown in lectures
SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SRC, ".."))
#ROOT = "C:/Users/DELL/Documents/UNI/Year_4/BEE2041 Data Science in Economics/rje215_project/"
DAT  = ROOT+"/data/"
FIG  = ROOT+"/results/figures/"
TAB  = ROOT+"/results/tables/"

# Import libraries:
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import statsmodels.api as sm
import seaborn as sns
import re
import warnings
from datetime import datetime 
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Patch
from tabulate import tabulate
from urllib import request, error
from bs4 import BeautifulSoup

#------------------------------------------------------------------------------
#--- (1) Webscrape data and save to CSV files
#------------------------------------------------------------------------------

# I did a placement year working in statistical programming for clinical trials, and working with patient data. To create datasets we often used lots of flags, 
# hence the flagging method used below, which is dissimilar to anything we looked at in class, hence I wanted to provide some reasoning to my potentially
# strange approach.

site = "https://en.wikipedia.org/wiki/List_of_world_records_in_athletics"
response = BeautifulSoup(request.urlopen(site), "html.parser")
tables = response.find_all("table", class_="wikitable")

#url = "https://en.wikipedia.org/wiki/List_of_world_records_in_athletics"
#headers = {"User-Agent": "Mozilla/5.0"}
#response = requests.get(url, headers=headers)
#soup = BeautifulSoup(response.text, "html.parser")

# Find men's and women's tables:
#tables = soup.find_all("table", {"class": "wikitable"})

def get_table(table):
    data = []
    current_event = None
    rowspan_count = 0
    
    # Get the header row:
    header_row = table.find_all("tr")[1]
    headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
    headers.insert(0, "Event")  # Insert Event as first column header
    
    # Process each table row, skippimg headers:
    for i, tr in enumerate(table.find_all("tr")):
        if i < 2:
            continue 
        
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        
        is_flagged = False
        # Check for background flags in the row:
        row_style = tr.get("style", "").lower()
        row_bgcolor = tr.get("bgcolor", "").lower()
        if "background:pink" in row_style or row_bgcolor in ["pink", "#cef6f5"]:
            is_flagged = True
        for td in cells:
            cell_style = td.get("style", "").lower()
            cell_bgcolor = td.get("bgcolor", "").lower()
            if "background:pink" in cell_style or cell_bgcolor in ["pink", "#cef6f5"]:
                is_flagged = True
        
        row = []
        if cells[0].has_attr("rowspan"):
            current_event = cells[0].get_text(strip=True)
            rowspan_count = int(cells[0]["rowspan"]) - 1
            row.append(current_event)
            cells = cells[1:]
        elif rowspan_count > 0:
            row.append(current_event)
            rowspan_count -= 1
        else:
            current_event = cells[0].get_text(strip=True)
            row.append(current_event)
            cells = cells[1:]
        
        # Append rest of the cells' text:
        for cell in cells:
            row.append(cell.get_text(strip=True))
        
        # Add flag status at the end:
        row.append(is_flagged)
        data.append(row)
    
    # Create DataFrame and assign column names
    df = pd.DataFrame(data)
    if len(df.columns) > len(headers) + 1:
        for i in range(len(headers), len(df.columns) - 1):
            headers.append(f"Column_{i}")
    column_names = headers + ["Flagged"]
    df.columns = column_names[:len(df.columns)]

    # Remove flagged rows and drop flag column:
    df = df[df["Flagged"] == False].reset_index(drop=True)
    df = df.drop("Flagged", axis=1)

    # Only keep relevant columns;
    my_cols = list(set(range(0, 12)) - {3})
    df = df.iloc[:, my_cols]
    df.columns = ["Event", "Performance", "Wind", "Avg. speed mph (kmph)", 
                      "Pts", "Athlete", "Nationality", "Date", "Meeting", 
                      "Location", "Country"]

    return df

# Apply function to get men's and women's tables
df_men = get_table(tables[0])
df_women = get_table(tables[1])

df_men.to_csv(DAT + "world_records_men.csv", index=False)
df_women.to_csv(DAT + "world_records_women.csv", index=False)

#------------------------------------------------------------------------------
#--- (2) Read in CSV files and prepare for analysis
#------------------------------------------------------------------------------

# Read in csv files:
df_world_records_men = pd.read_csv(DAT + "world_records_men.csv")
df_world_records_women = pd.read_csv(DAT + "world_records_women.csv")
# country-and-continent-codes-list-csv from https://gist.github.com/stevewithington/20a69c0b6d2ff846ea5d35e5fc47f26c#file-country-and-continent-codes-list-csv-csv
df_continents = pd.read_csv(DAT + "country-and-continent-codes-list-csv.csv")
dobs = pd.read_csv(DAT + "dobs.csv")  
keely_data = pd.read_csv(DAT + "keely_data.csv")

# COUNTRY AND CONTINENTS SECTION

# Replace 'DNK' with 'DEN' in the Three_Letter_Country_Code column, for merge:
df_continents['Three_Letter_Country_Code'] = df_continents['Three_Letter_Country_Code'].replace('DNK', 'DEN')

# Add Soviet Union row for some older records:
soviet_union_row = pd.DataFrame({'Three_Letter_Country_Code': ['URS'], 
                                 'Country_Name': ['Soviet Union'], 
                                 'Continent_Name': ['Europe']})
df_continents = pd.concat([df_continents, soviet_union_row], ignore_index=True)


# Merge continent and full country name on for later analysis:
df_men_cont = pd.merge(df_world_records_men, df_continents[['Three_Letter_Country_Code', 'Country_Name', 'Continent_Name']], 
                     left_on='Nationality', right_on='Three_Letter_Country_Code', how='left')

df_women_cont = pd.merge(df_world_records_women, df_continents[['Three_Letter_Country_Code', 'Country_Name', 'Continent_Name']], 
                     left_on='Nationality', right_on='Three_Letter_Country_Code', how='left')

# EVENTS SECTION

# Replace 'Marathon[e]' with 'Marathon' in the Event column for tidiness
df_men_cont['Event'] = df_men_cont['Event'].replace('Marathon[e]', 'Marathon')
df_women_cont['Event'] = df_women_cont['Event'].replace('Marathon[e]', 'Marathon')

# Separate events into their types:
def classify_event(event):
    event_lower = str(event).lower()
    if any(sh in event_lower for sh in ['msh', 'milesh', 'relaysh', 'onsh', 'walksh']):
        return 'Other'
    if 'walk' in event_lower:
        return 'Walk'
    elif 'relay' in event_lower:
        return 'Relay'
    elif 'hurdles' in event_lower:  # Dedicated category for hurdles
        return 'Hurdles'
    elif re.search(r'\b(50|6[0-9]|[1-3][0-9]{2}|400) m\b', event_lower):
       return 'Sprints'
    elif re.search(r'\b(8[0-9]{2}|[1-2][0-9]{3}|3000)\b.*m', event_lower) or 'mile' in event_lower:
        return 'Middle Distance'
    elif any(keyword in event_lower for keyword in ['5000', '5 km', '10,000', '10 km', '50 km', '100 km', 'one hour', 'marathon']):
        return 'Long Distance'
    elif any(keyword in event_lower for keyword in ['jump', 'vault', 'shot', 'throw', 'heptathlon', 'decathlon']):
        return 'Field'
    else:
        return 'Other'

df_men_cont['Group'] = df_men_cont['Event'].apply(classify_event)
df_women_cont['Group'] = df_women_cont['Event'].apply(classify_event)

# AGE SECTION

# Convert record dates and DOBs to datetime format:
df_men_cont['Date'] = pd.to_datetime(df_men_cont['Date'], format='%d %b %Y', errors='coerce')
df_women_cont['Date'] = pd.to_datetime(df_women_cont['Date'], format='%d %b %Y', errors='coerce')
dobs_men = dobs[['Male Athlete', 'Male DOB']].copy()
dobs_women = dobs[['Female Athlete', 'Female DOB']].copy()
dobs_men['Male DOB'] = pd.to_datetime(dobs_men['Male DOB'], format='%d/%m/%Y')
dobs_women['Female DOB'] = pd.to_datetime(dobs_women['Female DOB'], format='%d/%m/%Y')

# Left join and create new age column:
df_men = df_men_cont.join(dobs_men.set_index('Male Athlete'), on='Athlete', how='left')
df_men['Age'] = (df_men['Date'] - df_men['Male DOB']).dt.days / 365.25
df_women = df_women_cont.join(dobs_women.set_index('Female Athlete'), on='Athlete', how='left')
df_women['Age'] = (df_women['Date'] - df_women['Female DOB']).dt.days / 365.25

# KEELY SECTION

# Filter to get rid of indoors:
keely = keely_data[keely_data['Indoor'].isnull()].copy()

# Convert values to the right formats:
keely.loc[:, 'Date'] = pd.to_datetime(keely['Date'], format="%d-%b-%y", errors="coerce")
def time_to_seconds(time_str):
    mins, secs = map(float, time_str.split(":"))
    return mins * 60 + secs
keely.loc[:, 'Perf_seconds'] = keely['Perf'].apply(time_to_seconds)

#------------------------------------------------------------------------------
#--- (3) Figure 1: Number of records broken in Olympic vs Non-Olympic Years
#------------------------------------------------------------------------------

# Extract Year:
df_men['Year'] = pd.to_datetime(df_men['Date'], format='%d %b %Y').dt.year
df_women['Year'] = pd.to_datetime(df_women['Date'], format='%d %b %Y').dt.year

# Men's stats:
olympic_years_men = df_men[((df_men['Year'] % 4 == 0) & (df_men['Year'] != 2020)) | (df_men['Year'] == 2021)].shape[0]
non_olympic_years_men = df_men[~(((df_men['Year'] % 4 == 0) & (df_men['Year'] != 2020)) | (df_men['Year'] == 2021))].shape[0]
total_records_men = olympic_years_men + non_olympic_years_men
olympic_percentage_men = (olympic_years_men / total_records_men) * 100
non_olympic_percentage_men = (non_olympic_years_men / total_records_men) * 100

# Women's stats:
olympic_years_women = df_women[((df_women['Year'] % 4 == 0) & (df_women['Year'] != 2020)) | (df_women['Year'] == 2021)].shape[0]
non_olympic_years_women = df_women[~(((df_women['Year'] % 4 == 0) & (df_women['Year'] != 2020)) | (df_women['Year'] == 2021))].shape[0]
total_records_women = olympic_years_women + non_olympic_years_women
olympic_percentage_women = (olympic_years_women / total_records_women) * 100
non_olympic_percentage_women = (non_olympic_years_women / total_records_women) * 100

# Data frame:
year_data = pd.DataFrame({
    'Category': ['Olympic Year', 'Non-Olympic Year'],
    'Men': [olympic_years_men, non_olympic_years_men],
    'Men_Percentage': [olympic_percentage_men, non_olympic_percentage_men],
    'Women': [olympic_years_women, non_olympic_years_women],
    'Women_Percentage': [olympic_percentage_women, non_olympic_percentage_women]
})

# Plotting:
bar_width = 0.4
x = range(len(year_data['Category']))  # Positions for the bars

plt.bar(x, year_data['Men'], width=bar_width, label='Men', color='blue', alpha=0.8)
plt.bar([p + bar_width for p in x], year_data['Women'], width=bar_width, label='Women', color='pink', alpha=0.8)

# Annotations:
for i, (count, percentage) in enumerate(zip(year_data['Men'], year_data['Men_Percentage'])):
    plt.text(i, count + 1, f'{count} ({percentage:.1f}%)', ha='center', fontsize=10, color='black')
for i, (count, percentage) in enumerate(zip(year_data['Women'], year_data['Women_Percentage'])):
    plt.text(i + bar_width, count + 1, f'{count} ({percentage:.1f}%)', ha='center', fontsize=10, color='black')
plt.ylim(0, max(year_data['Men']) + 5)

# Format:
plt.xticks([p + bar_width / 2 for p in x], year_data['Category'])
plt.ylabel('Count')
plt.title('World Records Set in Olympic Years vs Non-Olympic Years (Men vs Women)')
plt.legend()

# Save:
plt.savefig(FIG + "olympic_years.png") 
plt.clf()

#------------------------------------------------------------------------------
#--- (4) Figure 2: Gender Gap across Events
#------------------------------------------------------------------------------

# Separate into time measured / distance measured:
gap_time = ['100 m', '200 m', '800 m', '5000 m', '10,000 m', 'Half marathon', 'Marathon']
gap_dist = ['High jump', 'Long jump', 'Pole vault', 'Javelin throw', 'Discus throw', 'Hammer throw']

# Clean time events (convert to seconds):
#def time_to_seconds(t):
#    parts = t.split(':')
#    try:
#        parts = list(map(float, parts))
#        if len(parts) == 3:
#            return parts[0]*3600 + parts[1]*60 + parts[2]
#        elif len(parts) == 2:
#            return parts[0]*60 + parts[1]
#        else:
#            return float(parts[0])
#    except:
#        return None

def time_to_seconds(t):
    try:
        if pd.isna(t):  # Handle missing values (NaN)
            return None
        parts = t.split(':')
        parts = list(map(float, parts))
        if len(parts) == 3:  # HH:MM:SS.FFF
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:  # MM:SS.FFF
            return parts[0] * 60 + parts[1]
        else:  # Pure seconds or numeric string
            return float(parts[0])
    except Exception as e:
        print(f"Error converting time: {t}, {e}")
        return None

#df_men['Performance_sec'] = df_men['Performance'].apply(time_to_seconds)
df_men.loc[df_men['Event'].isin(gap_time), 'Performance_sec'] = df_men.loc[df_men['Event'].isin(gap_time), 'Performance'].apply(time_to_seconds)
df_women.loc[df_women['Event'].isin(gap_time), 'Performance_sec'] = df_women.loc[df_women['Event'].isin(gap_time), 'Performance'].apply(time_to_seconds)
#df_women['Performance_sec'] = df_women['Performance'].apply(time_to_seconds)

# Clean distance events (remove 'm' and convert to float):
df_men.loc[df_men['Event'].isin(gap_dist), 'Performance_m'] = df_men.loc[df_men['Event'].isin(gap_dist), 'Performance'].str.replace(' m', '', regex=False).astype(float)
df_women.loc[df_women['Event'].isin(gap_dist), 'Performance_m'] = df_women.loc[df_women['Event'].isin(gap_dist), 'Performance'].str.replace(' m', '', regex=False).astype(float)

# Calculate % diffs for track & field:
results = []
all_events = gap_time + gap_dist
for event in all_events:
    men_row = df_men[df_men['Event'] == event].iloc[0]
    women_row = df_women[df_women['Event'] == event].iloc[0]
    
    if event in gap_time:
        men_perf = men_row['Performance_sec']
        women_perf = women_row['Performance_sec']
        gap = ((women_perf - men_perf) / men_perf) * 100
        colour = 'mediumslateblue'
    else:  
        men_perf = float(men_row['Performance_m'])
        women_perf = float(women_row['Performance_m'])
        gap = ((men_perf - women_perf) / women_perf) * 100
        colour = 'seagreen'
    
    results.append({
        'Event': event,
        'Gender_Gap': gap,
        'Color': colour
    })

gender_gap_df = pd.DataFrame(results)

# Plot
plt.figure(figsize=(14, 6))
bars = plt.bar(gender_gap_df['Event'], gender_gap_df['Gender_Gap'], color=gender_gap_df['Color'])

# Labels:
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 0.01, f"{yval:.2f}%", ha='center', va='bottom', fontsize=9)

# y = 0 marker:
plt.axhline(y=0, color='red', linestyle='dashed')

# Legend:
legend_elements = [
    Patch(facecolor='red', label='Equal Performance'),
    Patch(facecolor='mediumslateblue', label='Track (Timed) Events'),
    Patch(facecolor='seagreen', label='Field (Measured) Events')
]
plt.legend(handles=legend_elements, loc="best")

# Formatting:
plt.xlabel("Event")
plt.ylabel("Performance Gap of Men's Record \nBettering Women's Record (%)")
plt.title("Gender Gap in Athletics World Records (Track & Field Events)")
plt.ylim(min(gender_gap_df['Gender_Gap']) - 10, max(gender_gap_df['Gender_Gap']) + 10)
plt.xticks(rotation=45)
plt.tight_layout()

# Save:
plt.savefig(FIG + "gender_gap.png") 
plt.clf()

#------------------------------------------------------------------------------
#--- (5) Figure 3: Distribution of Ages of Record Breakers
#------------------------------------------------------------------------------

# Plot histograms:
plt.figure(figsize=(12, 7))
plt.hist(df_men['Age'], bins=15, alpha=0.5, color='blue', label='Men')
plt.hist(df_women['Age'], bins=15, alpha=0.5, color='pink', label='Women')

# Format:
plt.xlabel("Age at Time of Record (Years)")
plt.ylabel("Frequency")
plt.title("Distribution of Ages at Record Breaking for Men and Women")
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Save:
plt.savefig(FIG+'ages_dist.png') 
plt.clf()

#------------------------------------------------------------------------------
#--- (6) Table 1: Average Ages of Record Breakers for Event Groups
#------------------------------------------------------------------------------

# Men's statistics for each group:
group_men = df_men[~df_men['Group'].isin(['Relay', 'Exclude', 'Other'])].groupby('Group')['Age'].agg(
    Mean='mean',
    Median='median',
    Min='min',
    Max='max'
).round(2).transpose()  # Transpose for easier formatting later


# Men's total statistics:
overall_men = df_men['Age'].agg(
    Mean='mean',
    Median='median',
    Min='min',
    Max='max'
).round(2).transpose().rename("Overall")
group_men['Overall'] = overall_men

# Women's statistics for each group:
group_women = df_women[~df_women['Group'].isin(['Relay', 'Exclude', 'Other'])].groupby('Group')['Age'].agg(
    Mean='mean',
    Median='median',
    Min='min',
    Max='max'
).round(2).transpose()

# Women's total statistics:
overall_women = df_women['Age'].agg(
    Mean='mean',
    Median='median',
    Min='min',
    Max='max'
).round(2).transpose().rename("Overall")
group_women['Overall'] = overall_women

# Table:
df_avg_ages = pd.concat([group_men, group_women], keys=['Men', 'Women'])

# Save:
with open(TAB + "avg_ages.html", "w") as f:
    f.write(df_avg_ages.to_html(index=False, border=1))

#------------------------------------------------------------------------------
#--- (7) Figure 4: Boxplot of above
#------------------------------------------------------------------------------

# Add a gender column to each DataFrame
df_men['Gender'] = 'Men'
df_women['Gender'] = 'Women'
ages = pd.concat([df_men, df_women], ignore_index=True).query("Group != 'Other' and Group != 'Relay'")

# Plot
plt.figure(figsize=(12, 6))
sns.boxplot(data=ages, x='Group', y='Age', hue='Gender', palette='Set2')
plt.title('Age Distribution by Event Group and Gender')
plt.xlabel('Group')
plt.ylabel('Age')
plt.tight_layout()

# Save:
plt.savefig(FIG+'ages_box.png') 
plt.clf()

#------------------------------------------------------------------------------
#--- (8) Figure 5: Length of time each record has stood, Men & Women
#------------------------------------------------------------------------------

# Get data ready for plots - filter, get year & sort:
def plot_df(df):
    df_groups = df[df['Group'] != 'Other'].copy()
    df_groups['Years Since'] = 2025 - pd.to_datetime(df_groups['Date'], format='%d %b %Y').dt.year
    df_sort = df_groups.sort_values(by='Years Since', ascending=False)
    groups = df_sort['Group'].astype('category')
    group_codes = groups.cat.codes
    colours = plt.cm.tab10(group_codes % 10)
    return df_sort, groups, colours

df_men_sort, men_groups, men_colours = plot_df(df_men)
df_women_sort, women_groups, women_colours = plot_df(df_women)

# Subplots:
fig, axes = plt.subplots(1, 2, figsize=(18, 10), sharex=True)

# Men's Plot:
axes[0].barh(df_men_sort['Event'], df_men_sort['Years Since'], color=men_colours, alpha=0.8)
axes[0].set_title('Men\'s Longest Standing World Records', fontsize = 14)
axes[0].set_xlabel('Years Since Record Was Set')
axes[0].invert_yaxis()
axes[0].grid(axis='x', linestyle='--', alpha=0.7)

# Women's Plot:
axes[1].barh(df_women_sort['Event'], df_women_sort['Years Since'], color=women_colours, alpha=0.8)
axes[1].set_title('Women\'s Longest Standing World Records', fontsize = 14)
axes[1].set_xlabel('Years Since Record Was Set')
axes[1].invert_yaxis()
axes[1].grid(axis='x', linestyle='--', alpha=0.7)

# Legend:
all_groups = sorted(set(men_groups.cat.categories) | set(women_groups.cat.categories))
legend_colors = [plt.cm.tab10(i % 10) for i in range(len(all_groups))]
handles = [plt.Rectangle((0, 0), 1, 1, color=color, alpha=0.8)
           for color in legend_colors]
fig.legend(handles, all_groups, title='Event Type', loc='upper center', ncol=len(all_groups))

plt.tight_layout(rect=[0, 0, 1, 0.95])

# Save:
plt.savefig(FIG+'longest_records.png') 
plt.clf()

#------------------------------------------------------------------------------
#--- (9) Scatter Plot of all of Keely Hodgkinson's 800m times
#------------------------------------------------------------------------------
# Define colours for each event:
event_colours = {
    'Olympic Games': 'gold',
    'World Athletics Championships': 'blue',
    'Diamond League': 'green',
    'European Athletics': 'purple',
    'UK Athletics': 'hotpink',
    'Commonwealth Games': 'red'
}
default_colour = 'gray'

# Plot:
plt.figure(figsize=(12, 7))

# To keep track of which events aren't 'significant':
plotted_indices = set()

# Plot significant events:
for event, colour in event_colours.items():
    subset = keely[keely['Meeting'].str.contains(event, case=False, na=False)]
    plt.scatter(subset['Date'], subset['Perf_seconds'], label=event, color=colour)
    plotted_indices.update(subset.index)

# Plot all others:
other_subset = keely[~keely.index.isin(plotted_indices)]
plt.scatter(other_subset['Date'], other_subset['Perf_seconds'], label='Other Events', color=default_colour)

# Format:
# Custom formatter to convert seconds to mm:ss.ss
def seconds_to_time_format(x, pos):
    minutes = int(x // 60)
    seconds = x % 60
    return f"{minutes}:{seconds:05.2f}"
plt.gca().yaxis.set_major_formatter(FuncFormatter(seconds_to_time_format))
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.xlabel("Date")
plt.ylabel("Performance (Minutes:Seconds)")
plt.title("Keely Hodgkinson's 800m Performances by Meeting")
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save:
plt.savefig(FIG+'keely_all.png') 
plt.clf()

#------------------------------------------------------------------------------
#--- (10) Trend in Keely Hodkindon's Diamond League times, OLS regression
#------------------------------------------------------------------------------

# Filter for Diamond League:
keely_DL = keely[keely['Meeting'].str.contains("Diamond League", case=False, na=False)].copy()

# Convert dates to numeric and do OLS regression:
x_numeric = mdates.date2num(keely_DL['Date'])
X = sm.add_constant(x_numeric)
Y = keely_DL['Perf_seconds']
model = sm.OLS(Y, X).fit()
# To remove warning message here for clean output:
warnings.filterwarnings("ignore", message="`kurtosistest` p-value may be inaccurate with fewer than 20 observations")

# Save summary table as an HTML file:
with open(TAB + "keely_summary.html", "w") as f:
    f.write("<html>\n<head><title>Model Summary</title></head>\n<body>\n")
    f.write("<pre>\n") 
    f.write(model.summary().as_text())
    f.write("\n</pre>\n</body>\n</html>")

# Trend line function:
coeffs = model.params
trend_line = np.poly1d([coeffs.iloc[1], coeffs.iloc[0]])

# Find intersection (113.28 = current WR in seconds):
record = 113.28
intersect_date = mdates.num2date((113.28 - coeffs.iloc[0]) / coeffs.iloc[1])

# Make sure LOBF goes across the right x-axis range:
extended_dates = pd.date_range(start='2021-01-01', end='2026-01-01', freq='ME')
extended_x_numeric = mdates.date2num(extended_dates)

# Plot:
plt.figure(figsize=(12, 7))
plt.scatter(keely_DL['Date'], keely_DL['Perf_seconds'], label="Diamond League", color="green")
plt.plot(extended_dates, trend_line(extended_x_numeric), color='black', linestyle='--', label="Trend Line")
plt.axhline(y = record, color='red', linestyle='dotted', label="World Record (1:53.28)")

# Add annotation:
plt.annotate(f"Predicted WR:\n{intersect_date.date()}", xy=(intersect_date, record), xytext=(intersect_date, record + 0.1), fontsize=10, ha='left')

# Format axes & plot:
def seconds_to_time_format(x, pos):
    mins = int(x // 60)
    secs = x % 60
    return f"{mins}:{secs:05.2f}"
plt.gca().yaxis.set_major_formatter(FuncFormatter(seconds_to_time_format))
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
plt.xlabel("Date")
plt.ylabel("Performance (Minutes:Seconds)")
plt.title("Keely Hodgkinson's Diamond League 800m Performances")
plt.legend()
plt.grid(True)

# Save:
plt.savefig(FIG+'keely_DL.png') 
plt.clf()