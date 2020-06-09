"""Web interface"""

import re

import pandas as pd
import streamlit as st
from textblob import TextBlob

import src.analyzer as az
import src.doc_similarity as ds
import src.markdown as md
import src.summarizer as sz
import src.topic_modeling as tm
import src.visualization as vis


# resources/cs100f2019_lab05_reflections
# resources/combined/lab1, resources/combined/lab2

# initialize main_df and preprocessed_Df
preprocessed_df = pd.DataFrame()
main_df = pd.DataFrame()


def main():
    """main streamlit function"""
    # Title
    st.sidebar.title("What to do")
    global directory
    global main_df
    directory = st.sidebar.text_input("Path to directory")
    directory = re.split(r'[;,\s]\s*', directory)
    if len(directory) == 0:
        st.sidebar.text("Please enter the path to the directory")
        with open("README.md") as readme_file:
            st.markdown(readme_file.read())
    elif directory != "":
        try:
            for item in directory:
                item_df = df_preprocess(item)
                main_df = main_df.append(item_df, ignore_index=True)
            st.sidebar.success(f"Analyzing {directory} ....")
            # st.write(main_df)
            global assignments
            assignments = st.sidebar.multiselect(
                label="Select assignments below:",
                options=main_df["Assignment"].unique()
            )
            global student_id
            student_id = st.sidebar.selectbox(
                label="Select primary key (the column holds student ids)",
                options=preprocessed_df.columns[1:]
            )
            analysis_mode = st.sidebar.selectbox(
                "Choose the analysis mode",
                [
                    "Home",
                    "Frequency Analysis",
                    "Sentiment Analysis",
                    "Document Similarity",
                    "Summary",
                    "Topic Modeling",
                ],
            )
            if analysis_mode == "Home":
                with open("README.md") as readme_file:
                    st.markdown(readme_file.read())
            if analysis_mode == "Frequency Analysis":
                st.title("Frequency Analysis")
                frequency()
            elif analysis_mode == "Sentiment Analysis":
                st.title("Sentiment Analysis")
                sentiment()
            elif analysis_mode == "Document Similarity":
                st.title("Document Similarity")
                doc_sim()
            elif analysis_mode == "Summary":
                st.title("Summary")
                summary()
            elif analysis_mode == "Topic Modeling":
                st.title("Topic Modeling")
                tpmodel()
        except FileNotFoundError as err:
            st.sidebar.text(err)
            with open("README.md") as readme_file:
                st.markdown(readme_file.read())


def df_preprocess(directory_path):
    "build and preprocess (combine, normalize, tokenize) text"
    original_df = pd.DataFrame(md.collect_md(directory_path))
    global preprocessed_df
    preprocessed_df = preprocessed_df.append(original_df, ignore_index=True)
    df_combined = original_df.copy(deep=True)
    # filter out first column -- user info
    cols = df_combined.columns[2:]
    # combining text into combined column
    df_combined["combined"] = df_combined[cols].apply(
        lambda row: "\n".join(row.values.astype(str)), axis=1
    )
    df_combined["normalized"] = df_combined["combined"].apply(lambda row: az.normalize(row))
    df_combined["tokens"] = df_combined["normalized"].apply(lambda row: az.tokenize(row))

    return df_combined


def frequency():
    """main function for frequency analysis"""
    freq_type = st.sidebar.selectbox(
        "Type of frequency analysis", ["Overall", "Student", "Question"]
    )
    if freq_type == "Overall":
        freq_range = st.sidebar.slider(
            "Select a range of Most frequent words", 1, 50, value=25
        )
        st.sidebar.success(
            'To continue see individual frequency analysis select "Individual"'
        )
        st.header(f"Overall most frequent words in **{', '.join(assignments)}**")
        overall_freq(freq_range)
    elif freq_type == "Student":
        freq_range = st.sidebar.slider(
            "Select a range of Most frequent words", 1, 20, value=10
        )
        st.header(f"Most frequent words by individual students in **{', '.join(assignments)}**")
        student_freq(main_df, freq_range)
    elif freq_type == "Question":
        freq_range = st.sidebar.slider(
            "Select a range of Most frequent words", 1, 20, value=10
        )
        st.header(f"Most frequent words in individual questions in **{', '.join(assignments)}**")
        question_freq(main_df, freq_range)


def sentiment():
    """main function for sentiment analysis"""
    senti_df = main_df.copy(deep=True)
    # calculate overall sentiment from the combined text
    senti_df["sentiment"] = senti_df["combined"].apply(
        lambda x: TextBlob(x).sentiment.polarity
    )
    senti_df = senti_df[senti_df["Assignment"].isin(assignments)]
    senti_type = st.sidebar.selectbox(
        "Type of sentiment analysis", ["Overall", "Student", "Question"]
    )
    if senti_type == "Overall":
        st.sidebar.success(
            'To continue see individual sentiment analysis select "Individual"'
        )
        st.header(f"Overall sentiment polarity in **{', '.join(assignments)}**")
        overall_senti(senti_df)
    elif senti_type == "Student":
        st.header(f"View sentiment by individual students in **{', '.join(assignments)}**")
        student_senti(senti_df)
    elif senti_type == "Question":
        st.header(f"View sentiment by individual questions in **{', '.join(assignments)}**")
        question_senti(senti_df)


def summary():
    """Display summarization"""
    summary_df = pd.DataFrame(sz.summarizer(directory))
    st.write(summary_df)


def tpmodel():
    """Display topic modeling"""
    topic_range = st.sidebar.slider(
        "Select the amount of topics", 1, 10, value=5
    )
    word_range = st.sidebar.slider(
        "Select the amount of words per topic", 1, 10, value=5
    )
    main_df["topics"] = main_df["combined"].apply(
        lambda x: tm.topic_model(
            x, NUM_TOPICS=topic_range, NUM_WORDS=word_range
        )
    )
    st.write(main_df[[student_id, "topics"]])


def doc_sim():
    """Display document similarity"""
    st.header("Similarity between each student's document")
    main_df["normal_text"] = main_df["combined"].apply(
        lambda x: az.normalize(x)
    )
    pairs = ds.create_pair(main_df[student_id])
    # calculate similarity of the docs of the selected author pairs
    similarity = [
        ds.tfidf_cosine_similarity(
            (
                main_df[main_df[student_id] == pair[0]][
                    "normal_text"].values[0],
                main_df[main_df[student_id] == pair[1]][
                    "normal_text"].values[0],
            )
        )
        for pair in pairs
    ]
    df_sim = pd.DataFrame({"pair": pairs, "similarity": similarity})
    # Split the pair tuple into two columns for plotting
    df_sim[['doc_1', 'doc_2']] = pd.DataFrame(
        df_sim['pair'].tolist(), index=df_sim.index
    )
    st.altair_chart(vis.doc_sim_heatmap(df_sim))


def overall_freq(freq_range):
    """page fore overall word frequency"""
    plots_range = st.sidebar.slider(
        "Select the number of plots per row", 1, 5, value=3
    )
    freq_df = pd.DataFrame(columns=["assignment", "word", "freq"])
    # calculate word frequency of each assignments
    for item in assignments:
        combined_text = " ".join(main_df[main_df["Assignment"] == item].normalized)
        item_df = pd.DataFrame(az.word_frequency(combined_text, freq_range),
                               columns=["word", "freq"])
        item_df["assignment"] = item
        freq_df = freq_df.append(item_df)
    # plot all the subplots of different assignments
    st.altair_chart(vis.facet_freq_barplot(
        freq_df, assignments, "assignment", plots_per_row=plots_range))


def student_freq(df_combined, freq_range):
    """page for individual student's word frequency"""
    students = st.multiselect(
        label="Select specific students below:",
        options=df_combined[student_id].unique()
    )

    plots_range = st.sidebar.slider(
        "Select the number of plots per row", 1, 5, value=3
    )
    freq_df = pd.DataFrame(columns=["student", "word", "freq"])
    stu_assignment = df_combined[(df_combined[student_id].isin(students)) & df_combined["Assignment"].isin(assignments)]
    if len(students) != 0:
        for student in students:

            individual_freq = az.word_frequency(
                stu_assignment[stu_assignment[student_id] == student]
                .loc[:, ["combined"]]
                .to_string(),
                freq_range,
            )
            ind_df = pd.DataFrame(individual_freq, columns=["word", "freq"])

            ind_df["student"] = student
            freq_df = freq_df.append(ind_df)

        st.altair_chart(vis.facet_freq_barplot(
            freq_df, students, "student", plots_per_row=plots_range))


def question_freq(input_df, freq_range):
    """page for individual question's word frequency"""
    # drop columns with all na
    select_preprocess = preprocessed_df[preprocessed_df["Assignment"].isin(assignments)].dropna(axis=1, how="all")
    questions = st.multiselect(
        label="Select specific questions below:",
        options=select_preprocess.columns[1:]
    )

    plots_range = st.sidebar.slider(
        "Select the number of plots per row", 1, 5, value=1
    )

    freq_question_df = pd.DataFrame(columns=["question", "word", "freq"])

    select_text = {}
    for question in questions:
        select_text[question] = input_df[question].to_string(index=False, na_rep="")
    question_df = pd.DataFrame(
        select_text.items(),
        columns=["question", "text"]
    )

    if len(questions) != 0:
        for question in questions:
            quest_freq = az.word_frequency(
                question_df[question_df["question"] == question]
                .loc[:, ["text"]]
                .to_string(),
                freq_range,
            )
            ind_df = pd.DataFrame(quest_freq, columns=["word", "freq"])
            ind_df["question"] = question
            freq_question_df = freq_question_df.append(ind_df)

        st.altair_chart(vis.facet_freq_barplot(
            freq_question_df,
            questions, "question", plots_per_row=plots_range))


def overall_senti(senti_df):
    """page for overall senti"""
    # display line plot when there are multiple assingments
    if len(assignments) > 1:
        st.altair_chart(vis.stu_senti_lineplot(senti_df, student_id))
    st.altair_chart((vis.senti_combinedplot(senti_df, student_id)))


def student_senti(input_df):
    """page for display individual student's sentiment"""
    students = st.multiselect(
        label="Select specific students below:",
        options=input_df[student_id].unique()
    )
    plots_range = st.sidebar.slider(
        "Select the number of plots per row", 1, 5, value=3
    )
    df_selected_stu = input_df.loc[input_df[student_id].isin(students)]
    senti_df = pd.DataFrame(
        df_selected_stu, columns=["Assignment", student_id, "sentiment"]
    )
    if len(students) != 0:
        st.altair_chart(vis.facet_senti_barplot(
            senti_df,
            students, student_id, plots_per_row=plots_range))
        st.altair_chart(vis.stu_senti_barplot(senti_df, student_id))


def question_senti(input_df):
    """page for individual question's sentiment"""
    select_preprocess = preprocessed_df[preprocessed_df["Assignment"].isin(assignments)].dropna(axis=1, how="all")
    questions = st.multiselect(
        label="Select specific questions below:",
        options=select_preprocess.columns[2:]
    )
    select_text = []
    for column in questions:
        select_text.append(input_df[column].to_string(index=False, na_rep=""))
    questions_senti_df = pd.DataFrame(
        {"questions": questions, "text": select_text}
    )
    # calculate overall sentiment from the combined text
    questions_senti_df["sentiment"] = questions_senti_df["text"].apply(
        lambda x: TextBlob(x).sentiment.polarity
    )
    if len(select_text) != 0:
        st.altair_chart(vis.question_senti_barplot(questions_senti_df))


if __name__ == "__main__":
    main()
