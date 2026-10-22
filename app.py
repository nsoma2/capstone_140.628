# Data Science for Public Health in Python
# Capstone Project
# COVID-19 cases by country

# Packages:
import streamlit as st
import pandas as pd
import plotly.express as px

# Add a title and intro text
st.title("COVID Dashboard")
st.text('This is a web app to allow for exploration of COVID-19 Cases and Deaths')
c1, c2 = st.columns(2)
with c1:
        st.subheader('How to use')
        st.markdown(
            "1. Locate **Dashboard Options** on the left. \n"
            "2. Choose a **View** (Global or United States). \n"
            "3. Pick a **Metric** (confirmed cases or deaths) and a **Count type** (daily or cumulative). \n"
            "4. **Add** one or more countries or states to compare them on the same chart. \n"
        )
with c2:
        st.subheader("About the data")
        st.markdown(
            "- Source: Johns Hopkins University [Center for Systems Science and Engineering "
            " (CSSE) COVID-19 repository]"
            "(https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data/csse_covid_19_time_series).\n"
            " - Data run from **January 22, 2020** to **March 10,2023**, when JHU stopped collecting. \n"
            
            " - CSSE reports cumulative totals; daily counts are the day-over-day difference. \n"
            
            " - Global files are summed across provinces to one row per country. \n"
           
            " - US files are summed across counties to one row per state."
        )


st.divider()


# DATA MANAGEMENT
BASE = ("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/"
        "csse_covid_19_data/csse_covid_19_time_series/")

GLOBAL_FILES = {
    "Confirmed cases - Global": "time_series_covid19_confirmed_global.csv",
    "Deaths - Global" :          "time_series_covid19_deaths_global.csv",
}

US_FILES = {
    "Confirmed cases - US" : "time_series_covid19_confirmed_US.csv",
    "Deaths - US": "time_series_covid19_deaths_US.csv",
}
@st.cache_data

# WIDE TO LONG - Data loading functions
### GLOBAL 
def load_global_series(filename):
    """Read one CSSE file, collapse provinces into countries, return long format."""
    df = pd.read_csv(BASE + filename)

    # the date columns start after the 4 columns in the global data
    date_cols = df.columns[4:]

    # collapse Provinces in order to have one row per country
    wide = df.groupby("Country/Region")[date_cols].sum()

    long = (wide.T
                .rename_axis("date")
                .reset_index()
                # using .melt to reshape from wide to long format
                .melt(id_vars="date", var_name="country", value_name="cumulative"))
    long["date"] = pd.to_datetime(long["date"], format="%m/%d/%y")

    # sort value by country and date
    long = long.sort_values(["country", "date"])

    # calculate new daily values from the cumulative total grouped by country
    long["daily"] = long.groupby("country")["cumulative"].diff().fillna(0)
    long["daily"] = long["daily"].clip(lower=0)

    return long

### US ONLY
def load_us_series(filename):
    """Read one CSSE file, collapse provinces into countries, return long format."""
    df = pd.read_csv(BASE + filename)

    # the date columns start after the 4 columns in the global data
    meta_cols = [
        "UID", "iso2", "iso3", "code3", "FIPS", "Admin2",
        "Province_State", "Country_Region", "Lat", "Long_",
        "Combined_Key", "Population",
    ]
    
    date_cols = [c for c in df.columns if c not in meta_cols]

    # collapse Provinces in order to have one row per country
    wide = df.groupby("Province_State")[date_cols].sum()

    long = (
        wide.T.rename_axis("date")
        .reset_index()
        .melt(id_vars="date", var_name="state", value_name="cumulative")
    )
    long["date"] = pd.to_datetime(long["date"], format="%m/%d/%y")
    long = long.sort_values(["state", "date"]).reset_index(drop=True)
    long["daily"] = long.groupby("state")["cumulative"].diff().fillna(0)
    long["daily"] = long["daily"].clip(lower=0)

    return long

# Build a stable color map such that colors don't shuffle when the user adds/removes items
def build_color_map(all_labels):
    palette = px.colors.qualitative.Plotly + px.colors.qualitative.D3
    return {
        label: palette[i % len(palette)]
        for i, label in enumerate(sorted(all_labels))
    }

# SIDE BAR CONTROLS

st.sidebar.header('Dashboard Options')

### View toggle: Global vs. United States
view = st.sidebar.selectbox(
    "View",
    ["Global (by County)", "United States (by State)"],
    index=0,
)

is_us = view.startswith("United States")

### Metric Selection
if is_us:
    metric = st.sidebar.selectbox("Metric", list(US_FILES.keys()))
else:
    metric = st.sidebar.selectbox("Metric", list(GLOBAL_FILES.keys()))

### Count type
mode= st.sidebar.selectbox("Count Type", ["Daily", "Cumulative"])

st.subheader("Dashboard")

# DATA LOADING
if is_us:
    ## United States View:
    df = load_us_series(US_FILES[metric])
    region_col = "state"
    all_regions = sorted(df["state"].unique())

    selected = st.multiselect(
        "Add US States/Territories",
        options = all_regions,
        default=["Maryland"],
        help="Start typing to search for a state."
    )
else:
    ## Global View:
    df = load_global_series(GLOBAL_FILES[metric])
    region_col = "country"
    all_regions = sorted(df["country"].unique())

    selected = st.multiselect(
        "Add Countries",
        options = all_regions,
        default = ["India"],
        help="Start typing to search for a country."
    )

if not selected:
    st.warning("Please select at least one region to display.")
    st.stop()



# PREPARE PLOT DATA
value_col = "daily" if mode == "Daily" else "cumulative"

plot_df = df[df[region_col].isin(selected)].copy()

value_label = f"{mode} {metric.lower()}"

color_map = build_color_map(all_regions)


# PLOT 
region_label = "State" if is_us else "Country"
title_regions = ", ".join(selected) if len(selected) <= 5 else f"{len(selected)} regions"
chart_title = f"{value_label.title()} — {title_regions}"

fig = px.bar(
    plot_df,
    x="date",
    y=value_col,
    color=region_col,
    color_discrete_map=color_map,
    title=chart_title,
    labels={
        value_col: value_label.title(),
        "date": "Date",
        region_col: region_label,
    },
)

fig.update_layout(
    hovermode="x unified",
    legend=dict(title=region_label, orientation="h", y=-0.15),
    margin=dict(t=50, b=80),
)


st.plotly_chart(fig, use_container_width=True)

# PEAK DATA IDENTIFIER
with st.popover("Peak Dates"):
    for region in selected:
        region_data = plot_df[plot_df[region_col] == region]
        peak_row = region_data.loc[region_data["daily"].idxmax()]
        st.write(
            f"**{region}:** Peak daily {metric.lower()} of "
            f"**{int(peak_row['daily']):,}** on "
            f"**{peak_row['date'].strftime('%B %d, %Y')}**"
        )
