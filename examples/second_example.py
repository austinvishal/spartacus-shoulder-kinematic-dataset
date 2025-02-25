from pandas import DataFrame

from spartacus import DataFolder, load_subdataset, DataFrameInterface, DataPlanchePlotting


def main():
    spartacus_dataset = load_subdataset(name=DataFolder.BEGON_2014)
    print(spartacus_dataset.confident_data_values)
    return spartacus_dataset.corrected_confident_data_values


def plot_mvt(df: DataFrame):

    humeral_motions = df["humeral_motion"].unique()

    for mvt in humeral_motions:
        sub_df = df[df["humeral_motion"] == mvt]
        dfi = DataFrameInterface(sub_df)
        plt = DataPlanchePlotting(dfi)
        plt.plot()
        plt.update_style()
        plt.show()


if __name__ == "__main__":
    data = main()
    plot_mvt(data)
