import streamlit as st
from streamlit_drawable_canvas import st_canvas
import pandas as pd
from helpers import (
    Play,
    PitchImage,
    get_table_download_link,
    download_data,
    visualize_data,
    visualize_pitch,
)
from pitch import FootballPitch

tags = {
    "Ball location @ pass start event -500 ms": "#000000",
    "Direct opponent @ pass start event -500 ms": "#00ffff",
    "Pass receiver @ pass start event -500ms": "#000000",
    "Interception candidate @ pass start event -500ms": "#ff00ff",
    "Ball location @ pass start event": "#000000",
    "Direct opponent @ pass start event": "#a52a2a",
    "Pass receiver @ pass start event": "#000000",
    "Interception candidate @ pass start event": "#808080",
    "Ball location @ pass end event": "#0000ff",
    "Direct opponent @ pass end event": "#a52a2a",
    "Pass receiver @ pass end event": "#000000",
    "Interception candidate @ pass end event": "#008000",
    "Body orientation # TODO": "#FFFFFF",
}

st.set_option("deprecation.showfileUploaderEncoding", False)
st.beta_set_page_config(page_title="BirdsPyView", layout="wide")

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

        with col1:
            canvas_image = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=2,
                stroke_color="#e00",
                background_image=snapshot.im,
                width=snapshot.im.width,
                height=snapshot.im.height,
                drawing_mode="line",
                key="canvas",
            )

        with col2:
            line_seq = ["UP", "DP", "RPA", "RG"]
            h_line_options = list(pitch.horiz_lines.keys())
            v_line_options = list(pitch.vert_lines.keys())

            hlines = [
                st.selectbox(
                    f"Horizontal Line #{x+1}",
                    h_line_options,
                    key=f"hline {x}",
                    index=h_line_options.index(line_seq[x]),
                )
                for x in range(2)
            ]
            vlines = [
                st.selectbox(
                    f"Vertical Line #{x+1}",
                    v_line_options,
                    key=f"vline {x}",
                    index=v_line_options.index(line_seq[x + 2]),
                )
                for x in range(2)
            ]

        with col3:
            st.image("pitch.png", width=300)

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

            # Writing to dataframe
            st.title("Players")
            st.write(
                "Draw rectangle over players on image. "
                + "The player location is assumed to the middle of the base of the rectangle."
            )

            p_col1, p_col2, p_col3 = st.beta_columns([2, 1, 1])

            # Dropdown boxes
            with p_col2:
                team_color = st.selectbox("Select Player: ", list(tags.keys()))
                stroke_color = tags[team_color]
                edit = st.checkbox("Edit mode (move selection boxes)")
                update = st.button("Update data")
                original = True  # st.checkbox('Select on original image', value=True)

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
                    dfCoords = pd.json_normalize(canvas_converted.json_data["objects"])
                    if original:
                        dfCoords["x"] = (
                            dfCoords["left"]
                            + (dfCoords["width"] * dfCoords["scaleX"]) / 2
                        )
                        dfCoords["y"] = (
                            dfCoords["top"] + dfCoords["height"] * dfCoords["scaleY"]
                        )
                        dfCoords[["x", "y"]] = snapshot.h.apply_to_points(
                            dfCoords[["x", "y"]].values
                        )
                    else:
                        dfCoords["x"] = (
                            dfCoords["left"] + dfCoords["width"] * dfCoords["scaleX"]
                        )
                        dfCoords["y"] = (
                            dfCoords["top"] + dfCoords["height"] * dfCoords["scaleY"]
                        )
                    dfCoords[["x", "y"]] = (
                        dfCoords[["x", "y"]] / snapshot.h.coord_converter
                    )
                    dfCoords["team"] = dfCoords.apply(
                        lambda x: {code: color for color, code in tags.items()}.get(
                            x["stroke"]
                        ),
                        axis=1,
                    )
                    dfCoords["time"] = t


if "dfCoords" in globals():
    download_data(dfCoords)
    visualize_data(dfCoords)

    print("have to transform data")

st.text("Adapted from https://github.com/rjtavares/BirdsPyView")