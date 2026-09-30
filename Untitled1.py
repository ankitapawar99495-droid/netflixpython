import base64
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


st.set_page_config(
	page_title="Netflix Insights",
	page_icon="N",
	layout="wide",
	initial_sidebar_state="expanded",
)

asset_dir = Path(__file__).resolve().parent
logo_path = asset_dir / "images.jpg"
background_path = asset_dir / "images (2).jpg"
logo_data = base64.b64encode(logo_path.read_bytes()).decode("ascii") if logo_path.exists() else ""
background_data = (
	base64.b64encode(background_path.read_bytes()).decode("ascii")
	if background_path.exists()
	else ""
)
background_image = (
	f"url('data:image/jpeg;base64,{background_data}')" if background_data else "none"
)
logo_markup = (
	f'<img class="dashboard-logo" src="data:image/jpeg;base64,{logo_data}" alt="Netflix logo">'
	if logo_data
	else '<div class="dashboard-kicker">Viewing patterns / 01</div>'
)

st.markdown(
	f"""
	<style>
	.stApp {{ background: #080808; color: #ffffff; }}
	[data-testid="stSidebar"] {{ background: #141414; }}
	.block-container {{ padding-top: 2rem; padding-bottom: 3rem; }}
	.dashboard-hero {{
		min-height: 245px; display: flex; align-items: flex-end;
		padding: 2rem; margin-bottom: 1.3rem; border-radius: 4px;
		background-image: linear-gradient(90deg, rgba(0,0,0,.86), rgba(0,0,0,.25)),
			linear-gradient(0deg, #080808 0%, transparent 65%), {background_image};
		background-size: cover; background-position: center 35%;
	}}
	.dashboard-hero-content {{ max-width: 600px; }}
	.dashboard-logo {{
		width: 150px; max-height: 85px; object-fit: contain;
		object-position: left center; display: block; margin-bottom: 1rem;
	}}
	.dashboard-kicker {{
		color: #e50914; font-size: 0.75rem; font-weight: 700;
		letter-spacing: 0.12em; text-transform: uppercase;
	}}
	.dashboard-title {{
		color: #ffffff; font-size: 2.35rem; font-weight: 700;
		line-height: 1.15; margin: 0.25rem 0 0.35rem;
	}}
	.dashboard-subtitle {{ color: #b3b3b3; margin-bottom: 1.5rem; }}
	div[data-testid="stMetric"] {{
		background: #141414; border: 1px solid #303030;
		padding: 1rem 1.1rem; border-radius: 6px;
	}}
	div[data-testid="stMetricLabel"] {{ color: #b3b3b3; }}
	div[data-testid="stMetricValue"] {{ color: #ffffff; }}
	h2 {{ padding-top: 0.7rem; }}
	</style>
	""",
	unsafe_allow_html=True,
)

st.markdown(
	f'''<section class="dashboard-hero">
		<div class="dashboard-hero-content">
			{logo_markup}
			<div class="dashboard-title">Netflix Insights</div>
			<div class="dashboard-subtitle">Explore revenue, ratings, and viewing activity across your audience.</div>
		</div>
	</section>''',
	unsafe_allow_html=True,
)

with st.sidebar:
	st.header("Data")
	uploaded_file = st.file_uploader("Upload a Netflix CSV", type=["csv"])
	st.caption("Expected fields include Region, Subscription_Plan, Category, Monthly_Revenue, Rating, and Watch_Date.")

	if uploaded_file is not None:
		try:
			netflix = pd.read_csv(uploaded_file)
		except Exception as error:
			st.error(f"Couldn't read this CSV: {error}")
			st.stop()
	else:
		csv_path = asset_dir / "netflix.csv"
		if not csv_path.exists():
			st.info("Upload your `netflix.csv` to view the dashboard.")
			st.stop()
		try:
			netflix = pd.read_csv(csv_path)
		except Exception as error:
			st.error(f"Couldn't read netflix.csv: {error}")
			st.stop()

if netflix.empty:
	st.warning("The CSV has no rows to analyze.")
	st.stop()

netflix = netflix.drop_duplicates().copy()
if "Watch_Date" in netflix.columns:
	netflix["Watch_Date"] = pd.to_datetime(netflix["Watch_Date"], errors="coerce")
for numeric_column in ("Monthly_Revenue", "Rating"):
	if numeric_column in netflix.columns:
		netflix[numeric_column] = pd.to_numeric(netflix[numeric_column], errors="coerce")

filtered = netflix.copy()
with st.sidebar:
	st.divider()
	st.header("Filters")
	filter_columns = ("Region", "Subscription_Plan", "Category")
	for column in filter_columns:
		if column in filtered.columns:
			values = sorted(filtered[column].dropna().astype(str).unique().tolist())
			selected = st.multiselect(column.replace("_", " "), values, default=values)
			if selected:
				filtered = filtered[filtered[column].astype(str).isin(selected)]
			else:
				filtered = filtered.iloc[0:0]

if filtered.empty:
	st.warning("No rows match the selected filters. Update the filters in the sidebar.")
	st.stop()

metric_columns = st.columns(3)
metric_columns[0].metric("Records", f"{len(filtered):,}")
if "Monthly_Revenue" in filtered.columns:
	total_revenue = filtered["Monthly_Revenue"].sum()
	metric_columns[1].metric("Monthly revenue", f"${total_revenue:,.2f}")
else:
	metric_columns[1].metric("Monthly revenue", "Unavailable")
if "Rating" in filtered.columns and filtered["Rating"].notna().any():
	metric_columns[2].metric("Average rating", f"{filtered['Rating'].mean():.2f}")
else:
	metric_columns[2].metric("Average rating", "Unavailable")

st.divider()
left_chart, right_chart = st.columns(2, gap="large")
chart_theme = {"background": "#141414", "view": {"stroke": "transparent"}}
axis_theme = alt.Axis(labelColor="#ffffff", titleColor="#ffffff", gridColor="#303030")

with left_chart:
	st.subheader("Revenue by region")
	if {"Region", "Monthly_Revenue"}.issubset(filtered.columns):
		region_data = (
			filtered.dropna(subset=["Region", "Monthly_Revenue"])
			.groupby("Region", as_index=False)["Monthly_Revenue"].sum()
			.sort_values("Monthly_Revenue", ascending=False)
		)
		chart = alt.Chart(region_data).mark_bar(color="#e50914", cornerRadiusEnd=3).encode(
			x=alt.X("Monthly_Revenue:Q", title="Revenue", axis=axis_theme),
			y=alt.Y("Region:N", sort="-x", title=None, axis=axis_theme),
			tooltip=["Region:N", alt.Tooltip("Monthly_Revenue:Q", format="$,.2f")],
		).properties(height=300, background=chart_theme["background"]).configure_view(stroke=None)
		st.altair_chart(chart, use_container_width=True)
	else:
		st.info("This chart needs Region and Monthly_Revenue columns.")

with right_chart:
	st.subheader("Ratings by subscription plan")
	if {"Subscription_Plan", "Rating"}.issubset(filtered.columns):
		plan_data = (
			filtered.dropna(subset=["Subscription_Plan", "Rating"])
			.groupby("Subscription_Plan", as_index=False)["Rating"].sum()
		)
		chart = alt.Chart(plan_data).mark_arc(innerRadius=65, outerRadius=115).encode(
			theta=alt.Theta("Rating:Q", stack=True),
			color=alt.Color(
				"Subscription_Plan:N",
				title="Plan",
				scale=alt.Scale(range=["#e50914", "#ffffff", "#8c8c8c", "#99070d", "#4d0000"]),
			),
			tooltip=["Subscription_Plan:N", alt.Tooltip("Rating:Q", format=".2f")],
		).properties(height=300, background=chart_theme["background"]).configure_view(stroke=None)
		st.altair_chart(chart, use_container_width=True)
	else:
		st.info("This chart needs Subscription_Plan and Rating columns.")

left_chart, right_chart = st.columns(2, gap="large")
with left_chart:
	st.subheader("Revenue by category")
	if {"Category", "Monthly_Revenue"}.issubset(filtered.columns):
		category_data = (
			filtered.dropna(subset=["Category", "Monthly_Revenue"])
			.groupby("Category", as_index=False)["Monthly_Revenue"].sum()
			.sort_values("Monthly_Revenue", ascending=False)
		)
		chart = alt.Chart(category_data).mark_bar(color="#e50914", cornerRadiusEnd=3).encode(
			x=alt.X("Monthly_Revenue:Q", title="Revenue", axis=axis_theme),
			y=alt.Y("Category:N", sort="-x", title=None, axis=axis_theme),
			tooltip=["Category:N", alt.Tooltip("Monthly_Revenue:Q", format="$,.2f")],
		).properties(height=300, background=chart_theme["background"]).configure_view(stroke=None)
		st.altair_chart(chart, use_container_width=True)
	else:
		st.info("This chart needs Category and Monthly_Revenue columns.")

with right_chart:
	st.subheader("Revenue by month")
	if {"Watch_Date", "Monthly_Revenue"}.issubset(filtered.columns):
		monthly_data = filtered.dropna(subset=["Watch_Date", "Monthly_Revenue"]).copy()
		monthly_data["Month"] = monthly_data["Watch_Date"].dt.to_period("M").dt.to_timestamp()
		monthly_data = monthly_data.groupby("Month", as_index=False)["Monthly_Revenue"].sum()
		chart = alt.Chart(monthly_data).mark_line(color="#e50914", point=alt.OverlayMarkDef(color="#ffffff", filled=True)).encode(
			x=alt.X("Month:T", title=None, axis=alt.Axis(labelColor="#ffffff", titleColor="#ffffff", gridColor="#303030")),
			y=alt.Y("Monthly_Revenue:Q", title="Revenue", axis=axis_theme),
			tooltip=[alt.Tooltip("Month:T", format="%b %Y"), alt.Tooltip("Monthly_Revenue:Q", format="$,.2f")],
		).properties(height=300, background=chart_theme["background"]).configure_view(stroke=None)
		st.altair_chart(chart, use_container_width=True)
	else:
		st.info("This chart needs Watch_Date and Monthly_Revenue columns.")

with st.expander("Inspect filtered data"):
	st.dataframe(filtered, use_container_width=True, hide_index=True)




