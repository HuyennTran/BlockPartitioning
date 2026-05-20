import streamlit as st

st.title("Block Partition Visualization")

st.sidebar.header("Upload Files")

video_file = st.sidebar.file_uploader(
    "Upload Video",
    type=["mp4"]
)

csv_file = st.sidebar.file_uploader(
    "Upload Partition CSV",
    type=["csv"]
)

st.write("Visualization Area")