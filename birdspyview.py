from dataclasses import dataclass
import streamlit as st
import pandas as pd
from helpers import (
    download_data,
    visualize_pitch,
    get_field_lines,
    get_converted_positional_data,
)
from pitch import FootballPitch
from streamlit_drawable_canvas import st_canvas

tags = {
    "Direct opponent @ Pre pass": "#00fff1",
    "Intended pass receiver @ Pre pass": "#00ffff2",
    "Interception candidate @ Pre pass": "#00fff3",
    "Ball @ Start pass": "#a52a2a",
    "Direct opponent @ Start pass": "#a52a2b",
    "Intended pass receiver @ Start pass": "#a52a2c",
    "Interception candidate @ Start pass": "#a52a2d",
    "Ball @ End pass": "#FFFFF1",
    "Direct opponent @ End pass": "#FFFFF2",
    "Pass receiver @ End pass": "#FFFFF3",
    "Interception candidate @ End pass": "#FFFFF4",
    "Body orientation # TODO": "#FFFFF5",
}

st.set_option("deprecation.showfileUploaderEncoding", False)
st.beta_set_page_config(page_title="BirdsPyView", layout="wide")


@dataclass
class SessionState:
    positional_data = pd.DataFrame(
        columns=[
            "team",
            "x",
            "y",
            "time",
            "player_name",
            "game_time",
            "player_role",
            "situation_id",
        ]
    )


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
    t, snapshot = visualize_pitch(uploaded_file, pitch)

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

            st.title("Players")
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
                edit = st.checkbox("Edit mode (move selection boxes)")
                original = True  # st.checkbox('Select on original image', value=True)
                situation_id = st.text_input("Situation ID (e.g. 1)")
                player_name = st.text_input("Interception candidate player name")
                player_role = st.selectbox(
                    "Interception candidate role",
                    [
                        "Direct opponent of pass sender",
                        "Direct opponent of pass receiver",
                        "any other",
                    ],
                    index=0,
                )
                game_time = st.text_input(
                    "Game time in MM:SS (e.g. 05:00)", max_chars=5
                )
                if len(game_time) < 5 & len(game_time) > 0:
                    st.warning(
                        "Game time has to have 5 character. use the format 00:00"
                    )

                update = st.button("Update data")

            image2 = snapshot.get_image(original)
            height2 = image2.height
            width2 = image2.width
            with p_col1:
                canvas_converted = st_canvas(
                    fill_color="rgba(255, 165, 0, 0.3)",
                    stroke_width=2,
                    stroke_color=stroke_color,
                    background_image=image2,
                    drawing_mode="transform" if edit else "rect",
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
                    dfCoords["time"] = t
                    dfCoords["player_name"] = player_name
                    dfCoords["game_time"] = game_time
                    dfCoords["player_role"] = player_role

                    columns_of_interest = dfCoords.loc[
                        :,
                        [
                            "team",
                            "x",
                            "y",
                            "time",
                            "player_name",
                            "game_time",
                            "player_role",
                            "situation_id",
                        ],
                    ]

                    session.positional_data = pd.concat(
                        [session.positional_data, columns_of_interest],
                        axis=0,
                    )

                    session.positional_data.drop_duplicates(
                        keep="last", ignore_index=True, inplace=True
                    )

if "dfCoords" in globals():
    st.title("Inspect raw dataframe")
    st.dataframe(session.positional_data)

    st.title("Downloda data")

    data = session.positional_data

    download_data(
        dfCoords,
        [
            "team",
            "x",
            "y",
            "time",
            "game_time",
            "player_name",
            "player_role",
            "situation_id",
        ],
    )

    if st.button("Clear all cached data"):
        session.positional_data = pd.DataFrame(columns=session.positional_data.columns)