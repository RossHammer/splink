import pandas as pd
from pandas.testing import assert_frame_equal

from splink.duckdb.duckdb_comparison_library import (
    exact_match,
)
from splink.duckdb.linker import DuckDBDataFrame, DuckDBLinker

df_1 = [
    {"unique_id": 1, "first_name": "Tom", "surname": "Fox", "dob": "1980-01-01"},
    {"unique_id": 2, "first_name": "Amy", "surname": "Lee", "dob": "1980-01-01"},
    {"unique_id": 3, "first_name": "Amy", "surname": "Lee", "dob": "1980-01-01"},
]

df_2 = [
    {"unique_id": 1, "first_name": "Bob", "surname": "Ray", "dob": "1999-09-22"},
    {"unique_id": 2, "first_name": "Amy", "surname": "Lee", "dob": "1980-01-01"},
]

df_1 = pd.DataFrame(df_1)
df_2 = pd.DataFrame(df_2)


def test_size_density_dedupe():
    settings = {
        "probability_two_random_records_match": 0.01,
        "link_type": "dedupe_only",
        "comparisons": [
            exact_match("first_name"),
            exact_match("surname"),
            exact_match("dob"),
        ],
    }
    linker = DuckDBLinker(df_1, settings)

    df_predict = linker.predict()
    df_clustered = linker.cluster_pairwise_predictions_at_threshold(df_predict, 0.9)

    df_result = linker._compute_cluster_metrics(
        df_predict, df_clustered, threshold_match_probability=0.9
    ).as_pandas_dataframe()

    data_expected = [
        {"cluster_id": 1, "n_nodes": 1, "n_edges": 0.0, "density": None},
        {"cluster_id": 2, "n_nodes": 2, "n_edges": 1.0, "density": 1.0},
    ]
    df_expected = pd.DataFrame(data_expected)

    assert_frame_equal(df_result, df_expected, check_index_type=False)


def test_size_density_link():
    settings = {
        "probability_two_random_records_match": 0.01,
        "link_type": "link_only",
        "comparisons": [
            exact_match("first_name"),
            exact_match("surname"),
            exact_match("dob"),
        ],
    }
    linker = DuckDBLinker(
        [df_1, df_2], settings, input_table_aliases=["df_left", "df_right"]
    )

    df_predict = linker.predict()
    df_clustered = linker.cluster_pairwise_predictions_at_threshold(df_predict, 0.9)

    df_result = (
        linker._compute_cluster_metrics(
            df_predict, df_clustered, threshold_match_probability=0.99
        )
        .as_pandas_dataframe()
        .sort_values(by="cluster_id")
        .reset_index(drop=True)
    )

    data_expected = [
        {
            "cluster_id": "df_left-__-1",
            "n_nodes": 1,
            "n_edges": 0.0,
            "density": None,
        },
        {
            "cluster_id": "df_left-__-2",
            "n_nodes": 3,
            "n_edges": 2.0,
            "density": 0.666667,
        },
        {
            "cluster_id": "df_right-__-1",
            "n_nodes": 1,
            "n_edges": 0.0,
            "density": None,
        },
    ]
    df_expected = (
        pd.DataFrame(data_expected).sort_values(by="cluster_id").reset_index(drop=True)
    )

    assert_frame_equal(df_result, df_expected, check_index_type=False)


def make_row(id_l: int, id_r: int, group_id: int, match_probability: float):
    return {
        "unique_id_l": id_l,
        "unique_id_r": id_r,
        "cluster_id": group_id,
        "match_probability": match_probability,
    }


def test_metrics():
    df_e = pd.DataFrame(
        [
            # group 1
            # 4 nodes, 4 edges
            make_row(1, 2, 1, 0.96),
            make_row(1, 3, 1, 0.98),
            make_row(1, 4, 1, 0.98),
            make_row(2, 4, 1, 0.98),
            # group 2
            # 6 nodes, 5 edges
            make_row(5, 6, 2, 0.96),
            make_row(5, 7, 2, 0.97),
            make_row(5, 9, 2, 0.99),
            make_row(7, 8, 2, 0.96),
            make_row(9, 10, 2, 0.96),
            # group 3
            # 2 nodes, 1 edge
            make_row(11, 12, 3, 0.99),
            # group 4
            # 11 nodes, 19 edges
            make_row(13, 14, 4, 0.99),
            make_row(13, 15, 4, 0.99),
            make_row(13, 16, 4, 0.99),
            make_row(13, 17, 4, 0.99),
            make_row(13, 18, 4, 0.99),
            make_row(13, 19, 4, 0.99),
            make_row(14, 15, 4, 0.99),
            make_row(14, 16, 4, 0.99),
            make_row(15, 16, 4, 0.99),
            make_row(15, 17, 4, 0.99),
            make_row(16, 18, 4, 0.99),
            make_row(16, 20, 4, 0.99),
            make_row(17, 21, 4, 0.99),
            make_row(18, 19, 4, 0.99),
            make_row(18, 21, 4, 0.99),
            make_row(18, 22, 4, 0.99),
            make_row(20, 22, 4, 0.99),
            make_row(20, 23, 4, 0.99),
            make_row(22, 23, 4, 0.99),
            # edges that don't make the cut
            # these should affect nothing
            make_row(1, 8, None, 0.94),
            make_row(2, 3, None, 0.92),
            make_row(5, 10, None, 0.93),
            make_row(4, 11, None, 0.945),
            make_row(5, 16, None, 0.9),
            make_row(7, 20, None, 0.93),
            make_row(17, 20, None, 0.92),
        ]
    )
    df_c = pd.DataFrame(
        [{"cluster_id": 1, "unique_id": i} for i in range(1, 4 + 1)]
        + [{"cluster_id": 2, "unique_id": i} for i in range(5, 10 + 1)]
        + [{"cluster_id": 3, "unique_id": i} for i in range(11, 12 + 1)]
        + [{"cluster_id": 4, "unique_id": i} for i in range(13, 23 + 1)]
    )
    # pass in dummy frame to linker
    linker = DuckDBLinker(df_1, {"link_type": "dedupe_only"})
    df_predict = DuckDBDataFrame("predict", "df_e", linker)
    df_clustered = DuckDBDataFrame("clusters", "df_c", linker)

    df_cm = linker._compute_cluster_metrics(
        df_predict, df_clustered, 0.95
    ).as_pandas_dataframe()

    expected = [
        {"cluster_id": 1, "n_nodes": 4, "n_edges": 4},
        {"cluster_id": 2, "n_nodes": 6, "n_edges": 5},
        {"cluster_id": 3, "n_nodes": 2, "n_edges": 1},
        {"cluster_id": 4, "n_nodes": 11, "n_edges": 19},
    ]
    for expected_row_details in expected:
        relevant_row = df_cm[df_cm["cluster_id"] == expected_row_details["cluster_id"]]
        assert relevant_row["n_nodes"].iloc[0] == expected_row_details["n_nodes"]
        assert relevant_row["n_edges"].iloc[0] == expected_row_details["n_edges"]
        assert relevant_row["density"].iloc[0] == (
            2
            * expected_row_details["n_edges"]
            / (expected_row_details["n_nodes"] * (expected_row_details["n_nodes"] - 1))
        )

    expected_node_degrees = [
        (1, 3),
        (2, 2),
        (3, 1),
        (4, 2),
        (5, 3),
        (6, 1),
        (7, 2),
        (8, 1),
        (9, 2),
        (10, 1),
        (11, 1),
        (12, 1),
        (13, 6),
        (14, 3),
        (15, 4),
        (16, 5),
        (17, 3),
        (18, 5),
        (19, 2),
        (20, 3),
        (21, 2),
        (22, 3),
        (23, 2),
    ]
    df_nm = linker._compute_node_metrics(
        df_predict, 0.95
    ).as_pandas_dataframe()


    for unique_id, expected_node_degree in expected_node_degrees:
        relevant_row = df_nm[df_nm["composite_unique_id"] == unique_id]
        print(unique_id)
        print(expected_node_degree)
        print(relevant_row)
        assert relevant_row["node_degree"].iloc[0] == expected_node_degree
