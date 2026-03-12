import marimo

__generated_with = "0.19.1"
app = marimo.App(width="full", app_title="Brow Lady Microblading Studio")

with app.setup:
    # Initialization code that runs before all other cells
    import marimo as mo
    import polars as pl
    import os
    import re
    import io
    import altair as alt
    from datetime import datetime
    from zoneinfo import ZoneInfo


@app.cell
def _():
    if mo.app_meta().mode == "edit":
        mode = mo.Html("Mode: EDIT / DEBUG")
    else:
        mode = None

    mode
    return


@app.cell
def _():
    header_md = """
    <div class="header">

      <!-- Logo -->
      <img class="header-logo"
           src="https://raw.githubusercontent.com/mohitshrestha/brand/refs/heads/main/logo/logo.png"
           alt="Mohit Shrestha Logo" />

      <!-- Brand Details -->
      <div class="header-details">
        <span class="brand-title">Mohit Shrestha - Analytics</span>
        <span class="brand-tagline">Building data-driven solutions</span>
      </div>

    </div>

    <style>
    .header {
      display: flex;
      align-items: center;
      justify-content: center;
      flex-wrap: wrap;
      gap: 2vw;
      width: 100%;
      max-width: 100%;
      padding: 2vw 1vw;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    .header-logo {
      height: clamp(100px, 12vw, 160px);
      object-fit: contain;
    }

    .header-details {
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

    .brand-title {
      font-size: clamp(22px, 4vw, 36px);
      font-weight: 700;
      line-height: 1.1;
    }

    .brand-tagline {
      font-size: clamp(14px, 2vw, 20px);
      color: #555;
      margin-top: 0.3em;
    }

    /* Responsive adjustments */
    @media (max-width: 700px) {
      .header {
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 4vw;
        padding: 4vw 3vw;
      }
    }
    </style>
    """

    mo.md(header_md)
    return


@app.cell
def _():
    # -----------------------------
    # File Upload for Data
    # -----------------------------
    # File upload widget
    file_upload_data = mo.ui.file(kind="area", filetypes=[".csv", ".xlsx"], multiple=False, label="Data File:<br> Drag and drop file here or click to open file browser")
    return (file_upload_data,)


@app.cell
def _():

    # -----------------------------
    # File Upload for References/Mappings
    # -----------------------------
    # File upload widget
    file_upload_references = mo.ui.file(kind="area", filetypes=[".csv", ".xlsx"], multiple=False, label="Reference File for Mappings:<br> Drag and drop file here or click to open file browser")
    return (file_upload_references,)


@app.cell
def _(file_upload_data, file_upload_references):
    grid = mo.hstack(
                [file_upload_data, file_upload_references], justify="center"
            )

    mo.md(
        f"""
        <div style="text-align: center; font-weight: bold;">Define variable values:</div>
        {grid}
        """
    )
    return

@app.cell
def _():
    # -----------------------------
    # Configuration
    # -----------------------------
    SCHEMA_OVERRIDES = {
        "Start Time": pl.Utf8,
        "End Time": pl.Utf8,
        "Phone": pl.Utf8,
        "Appointment Price": pl.Utf8,
        "Amount Paid Online": pl.Utf8,
        "Certificate Code": pl.Utf8,
        "Date Scheduled": pl.Utf8,
        "Label": pl.Utf8,
        "Date Rescheduled": pl.Utf8,
        "Appointment ID": pl.Int64,
    }
    return (SCHEMA_OVERRIDES,)


@app.cell
# -----------------------------
# File Loading
# -----------------------------
@app.cell
def load_file(file_widget, schema_overrides: dict) -> pl.DataFrame | None:
    """
    Load the first uploaded CSV or Excel file into a Polars DataFrame.
    Returns None if no file is uploaded.
    """
    # Try to get the first file
    file_bytes = file_widget.contents(0)
    file_name = file_widget.name(0)

    # Check if a file was actually uploaded
    if file_bytes is None or file_name is None:
        return None

    if file_name.lower().endswith(".csv"):
        df = pl.read_csv(io.BytesIO(file_bytes), schema_overrides=schema_overrides)
    elif file_name.lower().endswith((".xls", ".xlsx")):
        df = pl.read_excel(io.BytesIO(file_bytes), schema_overrides=schema_overrides)
    else:
        raise ValueError(f"Unsupported file type: {file_name}")

    return df



@app.cell
def _():
    # -----------------------------
    # Utility Functions
    # -----------------------------
    def format_phone(s: str) -> str:
        """Normalize phone numbers to +1 (XXX) XXX-XXXX format."""
        digits = ''.join(filter(str.isdigit, s or ""))
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) < 10:
            digits = digits.zfill(10)
        if len(digits) == 10:
            return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return s or "N/A"

    def to_snake_case(name: str) -> str:
        """Convert string to snake_case."""
        name = re.sub(r"[^\w\s]", "", name)  # remove special characters
        name = re.sub(r"\s+", "_", name)     # replace spaces with underscore
        return name.lower()

    def clean_column_names(df: pl.DataFrame) -> pl.DataFrame:
        """Rename all columns to snake_case."""
        new_names = {col: to_snake_case(col) for col in df.columns}
        return df.rename(new_names)
    return clean_column_names, format_phone


@app.cell
def _(clean_column_names, format_phone):
    # -----------------------------
    # Data Cleaning
    # -----------------------------
    def clean_data(df: pl.DataFrame) -> pl.DataFrame:
        """
        Clean and transform appointment data:
        - Parse datetime columns safely
        - Normalize text columns
        - Format phone numbers
        - Add concatenated fields
        """
        df = df.with_columns([
            # Parse Start Time and End Time with correct format, fallback to null if parsing fails
            pl.col("Start Time").str.strptime(
                pl.Datetime, "%B %d, %Y %I:%M %p", strict=False
            ).dt.replace_time_zone("America/New_York"),

            pl.col("End Time").str.strptime(
                pl.Datetime, "%B %d, %Y %I:%M %p", strict=False
            ).dt.replace_time_zone("America/New_York"),

            # Normalize text columns
            pl.col("First Name").str.to_titlecase().fill_null("N/A"),
            pl.col("Last Name").str.to_titlecase().fill_null("N/A"),
            pl.col("Phone").fill_null("N/A"),
            pl.col("Email").fill_null("N/A"),
            pl.col("Type").str.to_titlecase(),
            pl.col("Calendar").str.to_titlecase(),
            pl.col("Paid?").str.to_titlecase(),
            pl.col("Label").str.to_titlecase(),

            # Parse date columns safely
            pl.col("Date Scheduled").str.strptime(pl.Date, "%Y-%m-%d", strict=False),
            pl.col("Date Rescheduled").str.strptime(pl.Date, "%Y-%m-%d", strict=False),

            # Clean numeric columns
            pl.col("Appointment Price").str.replace_all(",", "").cast(pl.Float64),
            pl.col("Amount Paid Online").str.replace_all(",", "").cast(pl.Float64),
        ])

        # Standardize column names
        df = clean_column_names(df)

        # Format phone numbers
        df = df.with_columns(
            pl.col("phone")
            .str.replace_all(r"\D", "")
            .str.slice(-10)
            .str.pad_start(10, "0")
            .str.replace(r"(\d{3})(\d{3})(\d{4})", r"+1 (\1) \2-\3")
            .alias("phone")
        )


        # Add concatenated fields
        df = df.with_columns([
            pl.concat_str(["first_name", "last_name"], separator=" ").alias("full_name"),
            pl.concat_str(["first_name", "phone"], separator="; ").alias("first_name_and_phone"),
            pl.concat_str(["first_name", "email"], separator="; ").alias("first_name_and_email"),
        ])

        return df
    return (clean_data,)


@app.cell
def _(clean_data, file_upload_data, load_file):
    # Load uploaded file
    df_data = load_file(file_upload_data)

    if df_data is None:
        df_data_clean = None
    else:
        # Clean and transform data
        df_data_clean = clean_data(df_data)

    # Preview cleaned data
    # df_data_clean
    return (df_data_clean,)


@app.cell
def _(clean_column_names):
    # -----------------------------
    # Data Cleaning
    # -----------------------------
    def clean_references(df: pl.DataFrame) -> pl.DataFrame:
        """
        Clean and transform appointment data:
        - Parse datetime columns
        - Normalize text columns
        - Format phone numbers
        - Add concatenated fields
        """
        df = df.with_columns([
            pl.col("Type").str.to_titlecase(),
            pl.col("Include or not include").str.to_titlecase(),
            pl.col("Revised Type").str.to_titlecase(),
            pl.col("Initial / Touch up").str.to_titlecase(),
            pl.col("Free Touch Up").str.to_titlecase(),
        ])

        # Standardize column names
        df = clean_column_names(df)

        return df
    return (clean_references,)


@app.cell
def _(clean_references, file_upload_references, load_file):
    # Load uploaded file
    df_references = load_file(file_upload_references)

    if df_references is None:
        df_references_clean = None
    else:
        # Clean and transform data
        df_references_clean = clean_references(df_references)

    # Preview cleaned data
    # df_references_clean
    return (df_references_clean,)


@app.cell
def _(df_data_clean, df_references_clean):
    if df_data_clean is None or df_references_clean is None:
        df = None
    else:
        df = df_data_clean.join(df_references_clean, on = "type", how = "left")
    # df
    return (df,)


@app.cell
def _():
    include_or_not_include = mo.ui.dropdown(options=["Yes", "No", None],
        value="Yes",
        label="Select include_or_not_include",
        searchable=True,
    )

    if mo.app_meta().mode == "edit":
        status_include_or_not_include = include_or_not_include
    else:
        status_include_or_not_include = None

    status_include_or_not_include
    return (include_or_not_include,)


@app.cell
def _(df, result):
    if result is None or result.is_empty():
        records_status_section = mo.md(
            """
            <h2 style="text-align: center;">Records Status</h2>
            <p style="text-align: center;">⬆ Please upload both Data and Reference file to continue.<br> 
            No data to display yet.</p>
            """)
    else:
        # Normalize column for comparison
        col_normalized = pl.col("include_or_not_include").str.strip_chars().str.to_lowercase()

        # Count records
        records_to_keep = df.filter(col_normalized == "yes").height
        records_to_drop = df.filter(col_normalized == "no").height
        records_unknown = df.filter(
            col_normalized.is_null() | (~col_normalized.is_in(["yes", "no"]))
        ).height

        # Display stats
        records_to_keep_value = mo.stat(
            value=records_to_keep, label="Kept", caption="number of records", bordered=True
        )
        records_to_drop_value = mo.stat(
            value=records_to_drop, label="Dropped", caption="number of records", bordered=True
        )
        records_unknown_value = mo.stat(
            value=records_unknown, label="Needs Review", caption="number of records", bordered=True
        )

        records_status_data_grid = mo.hstack(
            [records_to_keep_value, records_to_drop_value, records_unknown_value],
            justify="center",
        )

        records_status_section = mo.md(
            f"""
            <h2 style="text-align: center;">Records Status</h2>
            {records_status_data_grid}
            """
        )

    records_status_section
    return


@app.cell
def _():
    mo.md(r"""
    **Unique Individual Identification (Default Logic):**
    - Grouping in this order, where order matters:
      1. calendar
      2. first_name
      3. phone
    """)
    return


@app.cell
def _():
    group_by = mo.ui.multiselect(
            options=["calendar", "first_name", "last_name", "phone", "email"],
            label="How to identify Unique Individual: Choose columns to group by",
            value =["calendar", "first_name", "phone"],
        )

    if mo.app_meta().mode == "edit":
        status_group_by = group_by
    else:
        status_group_by = None

    status_group_by
    return (group_by,)


@app.cell
def _(group_by):
    sort_by = group_by.value + ["start_time"]
    return (sort_by,)


@app.cell
def _(df, group_by, include_or_not_include, sort_by):
    if df is None or df.is_empty():
        result = None
        result_section = mo.md(
            """
            <h2 style="text-align: center;">Final Table for Exploratory Analysis</h2>
            <p style="text-align: center;">No data to display yet.</p>
            """)
    else:
        # Step 1: Sort
        data_sorted = df.sort(sort_by)

        # Step 2: Filter include_or_not_include (case-insensitive)
        data_sorted = data_sorted.filter(
            pl.when(include_or_not_include.value is None)
            .then(pl.col("include_or_not_include").is_null())
            .otherwise(
                pl.col("include_or_not_include")
                .str.strip_chars()
                .str.to_lowercase()
                == include_or_not_include.value.lower()
            )
        )

        # Step 3: Appointment number
        data_numbered = data_sorted.with_columns(
            (pl.col("start_time").cum_count().over(group_by.value))
            .alias("appointment_number")
        )

        # Step 4: Month difference
        df_final = data_numbered.with_columns([
            pl.col("start_time").dt.year().alias("year"),
            pl.col("start_time").dt.month().alias("month"),
        ]).with_columns([
            (
                (pl.col("year") - pl.col("year").shift(1)).over(group_by.value) * 12
                + (pl.col("month") - pl.col("month").shift(1)).over(group_by.value)
            ).alias("months_since_last_appointment")
        ])

        # Step 5: Final result
        result = df_final.select([
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "calendar",
            "type",
            "revised_type",
            "start_time",
            "appointment_number",
            "months_since_last_appointment",
        ])

        result = result.with_columns(
            pl.col("appointment_number").max().over(group_by.value).alias("tmp_max")
        ).with_columns(
            pl.when(pl.col("appointment_number") == pl.col("tmp_max"))
            .then(pl.col("tmp_max"))
            .otherwise(None)
            .alias("max_appointment_number")
        ).drop("tmp_max")

        if mo.app_meta().mode == "edit":
            title = mo.md(
                """
                <h2 style="text-align: center;">
                    Final Table for Exploratory Analysis
                </h2>
                """
            )

            table_result = result

            result_section = mo.vstack(
                [title, table_result],
                justify="center"
            )
        else:
            result_section = mo.md(
                """
                <h2 style="text-align: center;">
                    ⬆ Please upload both Data and Reference files to continue.
                </h2>
                """
            )

    result_section
    return (result,)


@app.cell
def _(result):
    if result is None or result.is_empty():
        kpi_section = mo.md(
            """
            <h2 style="text-align: center;">Key Performance Indicators (KPIs)</h2>
            <p style="text-align: center;">No data to display yet.</p>
            """)
    else:
        # Compute KPIs
        total_appointments_records = result.height
        avg_appointments = result.select(pl.col("max_appointment_number").median()).item()
        max_appointments = result.select(pl.col("max_appointment_number").max()).item()

        total_appointments_records_value = mo.stat(
            value=total_appointments_records,
            label="Total Appointment Records",
            bordered=True,
        )

        avg_appointments_value = mo.stat(
            value=avg_appointments,
            label="Average Appointments",
            caption="per person",
            bordered=True,
        )

        max_appointments_value = mo.stat(
            value=max_appointments,
            label="Max Appointments",
            caption="per person",
            bordered=True,
        )

        kpi_data_grid = mo.hstack(
            [total_appointments_records_value, avg_appointments_value, max_appointments_value],
            justify="center",
        )

        kpi_section = mo.md(
            f"""
            <h2 style="text-align: center;">Key Performance Indicators (KPIs)</h2>
            {kpi_data_grid}
            """
        )

    kpi_section
    return (avg_appointments,)


@app.cell
def _(avg_appointments, result):
    if result is None or result.is_empty():
        histogram_section = mo.md(
            """
            <h2 style="text-align: center;">Client Appointment Distribution</h2>
            <p style="text-align: center;">No data to display yet.</p>
            """)
    else:

        # Step 1: Histogram bins in Polars
        bins = 10
        min_val = result['max_appointment_number'].min()
        max_val = result['max_appointment_number'].max()
        bin_width = (max_val - min_val) / bins

        # Add bin column
        binned_df = result.with_columns(
            ((pl.col("max_appointment_number") - min_val) // bin_width).cast(pl.Int64).alias("bin")
        )

        # Aggregate counts per bin
        hist_agg = (
            binned_df.group_by("bin")
            .agg(pl.count("max_appointment_number").alias("count"))
            .sort("bin")
            .with_columns([
                (pl.col("bin") * bin_width + min_val).alias("bin_start"),
                (pl.col("bin") * bin_width + min_val + bin_width).alias("bin_end")
            ])
        )

        # Most common bin for highlight
        max_count = hist_agg['count'].max()
        mode_bin = hist_agg.filter(pl.col("count") == max_count).to_dicts()[0]

        # Label slightly above tallest bin for floating average label
        label_y = max_count * 1.05


        # Step 2: Histogram chart
        hist_data = alt.Data(values=hist_agg.select(["bin_start", "bin_end", "count"]).to_dicts())

        hist_chart = alt.Chart(hist_data).mark_bar().encode(
            x=alt.X('bin_start:Q', title='Number of Appointments', bin=alt.Bin(extent=[min_val, max_val], step=bin_width)),
            x2='bin_end:Q',
            y=alt.Y('count:Q', title='Number of People'),
            tooltip=[
                alt.Tooltip('count:Q', title='Number of People'),
                alt.Tooltip('bin_start:Q', title='Appointments Range', format=".0f")
            ],
            color=alt.condition(
                alt.datum.bin_start == mode_bin['bin_start'],
                alt.value('#219ebc'),  # highlighted bin
                alt.value('#8ecae6')   # normal bars
            )
        ).properties(
            height=300,
            width='container',
            title='Client Appointment Distribution'
        )

        # ------------------------------
        # Step 4: Average line
        # ------------------------------
        avg_line = alt.Chart(alt.Data(values=[{"avg": avg_appointments}])).mark_rule(
            color='cyan', size=3
        ).encode(
            x='avg:Q',
            tooltip=[alt.Tooltip('avg:Q', title='Average Appointments')]
        )

        # Floating label above average line
        avg_label = alt.Chart(alt.Data(values=[{"avg": avg_appointments, "y": label_y}])).mark_text(
            color='cyan',
            align='center',
            fontWeight='bold'
        ).encode(
            x='avg:Q',
            y='y:Q',
            text=alt.Text('avg:Q', format=".1f")
        )

        histogram_chart = hist_chart + avg_line + avg_label

        histogram_section = mo.vstack(
            [
                mo.md("<h2 style='text-align:center;'>Client Appointment Distribution</h2>"),
                histogram_chart,
            ],
            justify="center",
        )

    histogram_section
    return


@app.cell
def _():
    """Display header for Individual Summary"""
    mo.md(r"# Individual Summary")
    return


@app.cell
def _(result):
    # Dropdown for client selection
    if result is None or result.is_empty():
        mo.md("⬆ Upload both Data and Reference files to enable client selection.")
        filter_by_full_name = None
    else:
        names_series = result["full_name"].drop_nulls().unique().sort()
        filter_by_full_name = mo.ui.dropdown.from_series(
            names_series,
            label="Select a client"  # no default selection
        )

    filter_by_full_name
    return (filter_by_full_name,)


@app.cell
def _(filter_by_full_name, result):
    # Initialize summary with a placeholder message
    summary = "Select a client from the dropdown above to see summary"

    # Filter the result table for selected client
    df_individual_summary = (
        result.filter(pl.col("full_name") == filter_by_full_name.value)
        if filter_by_full_name is not None and filter_by_full_name.value is not None
        else None
    )

    """Compute and display summary metrics for selected client"""
    if df_individual_summary is None or df_individual_summary.is_empty():
        mo.md("Select a client from the dropdown above to see summary.")
    else:
        # Today's date
        today = datetime.now(tz=ZoneInfo("America/New_York"))
        today_year = today.year
        today_month = today.month

        # Filter last appointments per client and pick the latest start_time
        last_appointments = (
            df_individual_summary
            .filter(pl.col("appointment_number") == pl.col("max_appointment_number"))
            .sort("start_time", descending=True)
            .group_by("full_name")
            .first()
            .with_columns([
                pl.col("start_time").alias("last_visit_dt"),
                pl.lit(today).alias("today"),
                ((pl.lit(today_year) - pl.col("start_time").dt.year()) * 12
                 + (pl.lit(today_month) - pl.col("start_time").dt.month()))
                .alias("months_since_last_visit")
            ])
            .with_columns([
                (
                    (pl.col("months_since_last_visit") // 12).cast(pl.Int64).cast(pl.Utf8) + " years " +
                    (pl.col("months_since_last_visit") % 12).cast(pl.Int64).cast(pl.Utf8) + " months"
                ).alias("months_since_last_visit_human")
            ])
        )

        # Pick the first row
        row = last_appointments.select([
            "last_visit_dt", "months_since_last_visit", "months_since_last_visit_human"
        ]).row(0)

        last_visit_dt = row[0]
        months_since_last = row[1]
        months_since_human = row[2]

        # Total appointments
        total_appointments = df_individual_summary.height

        # Display summary
        summary = (
            f"**Client Visit Summary**<br>"
            f"- **Today's date:** {today.strftime('%Y-%m-%d')}<br>"
            f"- **Last visit date:** {last_visit_dt.strftime('%Y-%m-%d')}<br>"
            f"- **Months since last visit:** {months_since_human} ({months_since_last} months)<br>"
            f"- **No. of Appointments:** {total_appointments}"
        )

    mo.md(summary)
    return (df_individual_summary,)


@app.cell
def _(df_individual_summary):
    # Details accordion
    mo.accordion({"View Details": df_individual_summary}, lazy=True)
    return


@app.cell
def _():
    footer_md = """
    <div class="footer">

      <div class="footer-left">
        <div class="brand">Mohit Shrestha</div>
        <div class="tagline">Data • AI • Analytics • Knowledge Sharing</div>

        <div class="support">
          <strong>Support my work</strong>
          <a class="kofi" href="https://ko-fi.com/mohitshrestha" target="_blank">
            <img src="https://cdn.prod.website-files.com/5c14e387dab576fe667689cf/670f5a01229bf8a18f97a3c1_favion.png" alt="Ko-fi">
            Buy me a coffee!
          </a>
        </div>
      </div>

      <div class="footer-right">
        <div class="follow">👉 Follow. Discover. Engage.</div>
        <div class="socials">
          <a href="https://www.linkedin.com/in/MohitShrestha/" target="_blank">
            <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/linkedin.svg" alt="LinkedIn">
          </a>
          <a href="https://x.com/MohitShrestha" target="_blank">
            <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/x.svg" alt="X">
          </a>
        </div>
      </div>

      <div class="footer-bottom">
        © 2026–present
        <a href="https://www.mohitshrestha.com.np" target="_top">MohitShrestha.com.np</a>
        • All rights reserved.
      </div>

    </div>

    <style>
    .footer {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 24px;
      max-width: 960px;
      margin: auto;
      padding: 24px 12px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    .footer-left,
    .footer-right {
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-width: 200px;
    }

    .brand {
      font-size: 18px;
      font-weight: 600;
    }

    .tagline {
      font-size: 13px;
      color: #555;
    }

    .kofi {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
    }

    .kofi img {
      width: 24px;
      height: 24px;
    }

    .socials {
      display: flex;
      gap: 12px;
      justify-content: center;
    }

    .socials a {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .socials img {
      width: 24px;
      height: 24px;
    }

    .footer-bottom {
      width: 100%;
      text-align: center;
      font-size: 12px;
      color: #555;
    }

    .footer a {
      color: #29abe0;
      text-decoration: underline;
    }

    /* Hover polish */
    .footer a:hover {
      opacity: 0.85;
      transform: translateY(-1px);
    }

    /* Mobile */
    @media (max-width: 700px) {
      .footer {
        flex-direction: column;
        align-items: center;
        text-align: center;
      }
      .socials {
        justify-content: center;
      }
    }
    </style>
    """
    mo.md(footer_md)
    return


if __name__ == "__main__":
    app.run()
