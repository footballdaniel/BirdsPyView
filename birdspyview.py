from dataclasses import dataclass
import streamlit as st
import pandas as pd
from helpers import (
    download_data,
    visualize_pitch,
    get_field_lines,
    get_converted_positional_data,
    VoronoiPitch,
    PitchDraw,
)
from pitch import FootballPitch
from streamlit_drawable_canvas import st_canvas

tags = {
    "Direct opponent of pass sender @ Pre pass": "#00fff1",
    "Intended pass receiver @ Pre pass": "#00ffff2",
    "Interception candidate @ Pre pass": "#00fff3",
    "Ball @ Start pass": "#a52a2a",
    "Direct opponent of pass sender @ Start pass": "#a52a2b",
    "Intended pass receiver @ Start pass": "#a52a2c",
    "Interception candidate @ Start pass": "#a52a2d",
    "Body orientation visual line @ Start pass": "#a52a2e",
    "Body orientation point 1 @ Start pass": "#FFFFF5",
    "Body orientation point 2 @ Start pass": "#FFFFF6",
    "Ball @ End pass": "#FFFFF1",
    "Intended Pass receiver @ End pass": "#FFFFF3",
    "Interception candidate @ End pass": "#FFFFF4",
    "Hypothetical pass end location @ End pass": "#FFFFF2",
}

columns_of_interest = [
    "team",
    "x",
    "y",
    "player_name",
    "pass_duration",
    "player_role",
    "situation_id",
    "facing_passing_line",
    "nationality",
]

st.set_option("deprecation.showfileUploaderEncoding", False)
st.beta_set_page_config(page_title="BirdsPyView", layout="wide")


@dataclass
class SessionState:
    positional_data = pd.DataFrame(columns=columns_of_interest)


@st.cache(allow_output_mutation=True)
def fetch_session():
    session = SessionState()
    return session


session = fetch_session()

st.title("Upload Image or Video")
uploaded_file = st.file_uploader(
    "Select Image file to open:", type=["png", "jpg", "mp4"]
)
pitch = FootballPitch()


if uploaded_file:
    snapshot = visualize_pitch(uploaded_file, pitch)

    st.title("Pitch lines")

    lines_expander = st.beta_expander(
        "Draw pitch lines on selected image (2 horizontal lines, then 2 vertical lines)",
        expanded=True,
    )
    with lines_expander:
        col1, col2, col_, col3 = st.beta_columns([2, 1, 0.5, 1])

        canvas_image, hlines, vlines = get_field_lines(
            pitch, snapshot, col1, col2, col3
        )

    if canvas_image.json_data is not None:
        n_lines = len(canvas_image.json_data["objects"])
        with col3:
            st.write(
                f"You have drawn {n_lines} lines. Use the Undo button to delete lines."
            )

        if n_lines >= 4:
            snapshot.set_info(
                pd.json_normalize(canvas_image.json_data["objects"]), hlines + vlines
            )

            with lines_expander:
                st.write("Converted image:")
                st.image(snapshot.conv_im)

            st.title("Annotate positional data")
            st.write(
                "Draw rectangle over players on image. "
                + "The player location is assumed to the middle of the base of the rectangle."
            )

            p_col1, p_col2, p_col3 = st.beta_columns([2, 1, 1])

            with p_col2:
                team_color = st.selectbox(
                    "Select Player to annotate position: ", list(tags.keys())
                )
                stroke_color = tags[team_color]
                is_facing_the_passingline = st.checkbox(
                    "Is the pass interception candidate facing the passing line?",
                    value=True,
                )
                original = True  # st.checkbox('Select on original image', value=True)
                situation_id = st.text_input("Situation ID (e.g. 1)", value="1")
                player_name = st.text_input(
                    "Interception candidate player name", value="NaN"
                )
                player_role = st.selectbox(
                    "Interception candidate role",
                    [
                        "Direct opponent of pass sender",
                        "Direct opponent of pass receiver",
                        "any other",
                    ],
                    index=0,
                )
                nationality = st.selectbox(
                    "Nationality of the interception candidate", ["NL", "BIH", "ITA"]
                )
                pass_duration = st.text_input(
                    "Pass duration in seconds and fraction of second (e.g. 0.50 for a 500ms pass)",
                    max_chars=4,
                    value="0.50",
                )
                if len(pass_duration) < 3 & len(pass_duration) > 0:
                    st.warning(
                        "Pass duration has to be indicated with the format S.FF (e.g. 0.50 s)"
                    )

                update = st.button("Update data")

            if team_color == "Body orientation visual line @ Start pass":
                body_orientation_lines = True
            else:
                body_orientation_lines = False

            image2 = snapshot.get_image(original)
            height2 = image2.height
            width2 = image2.width
            with p_col1:
                canvas_converted = st_canvas(
                    fill_color="rgba(255, 165, 0, 0.3)",
                    stroke_width=2,
                    stroke_color=stroke_color,
                    background_image=image2,
                    drawing_mode="line" if body_orientation_lines else "rect",
                    update_streamlit=update,
                    height=height2,
                    width=width2,
                    key="canvas2",
                )

            if canvas_converted.json_data is not None:
                if len(canvas_converted.json_data["objects"]) > 0:
                    dfCoords = get_converted_positional_data(
                        tags, snapshot, original, canvas_converted
                    )

                    # Add metadata to dataframe
                    dfCoords["situation_id"] = situation_id
                    dfCoords["pass_duration"] = pass_duration
                    dfCoords["player_name"] = player_name
                    dfCoords["pass_duration"] = pass_duration
                    dfCoords["player_role"] = player_role
                    dfCoords["facing_passing_line"] = is_facing_the_passingline
                    dfCoords["nationality"] = nationality

                    session.positional_data = pd.concat(
                        [session.positional_data, dfCoords[columns_of_interest]],
                        axis=0,
                    )

                    session.positional_data.drop_duplicates(
                        keep="last",
                        ignore_index=True,
                        inplace=True,
                    )

                    session.positional_data.drop_duplicates(
                        keep="first", ignore_index=True, inplace=True
                    )

                st.title("Overlay of positional data of current frame")
                voronoi = VoronoiPitch(dfCoords)

                sensitivity = 10
                player_circle_size = 2
                player_opacity = 100
                draw = PitchDraw(snapshot, original=True)
                for pid, coord in dfCoords.iterrows():
                    draw.draw_circle(
                        coord[["x", "y"]].values,
                        "black",
                        player_circle_size,
                        player_opacity,
                    )
                st.image(draw.compose_image(sensitivity))


if "dfCoords" in globals():
    st.title("Inspect raw dataframe")

    st.dataframe(session.positional_data)

    st.title("Downloda data")

    download_data(session.positional_data)

    if st.button("Clear all cached data"):
        session.positional_data = pd.DataFrame(columns=session.positional_data.columns)