import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from .constants import (
    BIOMECHANICAL_DOF_LEGEND,
    TRANSLATIONAL_BIOMECHANICAL_DOF_LEGEND,
    JOINT_ROW_COL_INDEX,
    AUTHORS_COLORS,
    AUTHOR_DISPLAYED_STUDY,
)
from .dataframe_interface import DataFrameInterface
from ..src.enums import JointType


def get_color(article):
    """
    Get the color of the article.
    If the article is not in the AUTHORS_COLORS dict, a random color is generated.
    """
    color = AUTHORS_COLORS.get(article)
    opacity = 0.5
    if color is None:
        print(f"Color not found for {article}. Generating a random color.")
        random_ints = np.random.randint(0, 255, 3).tolist() + [opacity]
        #     turn it in to a tuple[int]
        random_ints = tuple(random_ints)
        color = f"rgba{random_ints}"
    else:
        color = f"rgba{tuple(list(color) + [opacity])}"

    return color


class DataPlanchePlotting:
    def __init__(self, dfi: DataFrameInterface, restrict_to_joints: list[str | JointType] = None, options: dict = None):

        if dfi.has_translations_and_rotations:
            raise ValueError("The DataFrameInterface must contain only rotational data or translation data, not both.")

        self.rotations = dfi.has_rotational_data

        self.restrict_to_joints = restrict_to_joints

        self.fig = self.make_fig(rotation=self.rotations)

        self.dfi = dfi
        self.opacity = 0.85 if self.dfi.nb_articles > 1 else 1
        self.options = {"marker_symbol": ("in_vivo", ("circle", "diamond"))} if options is None else options

        self.showlegend = True

    @property
    def nb_joints(self):
        return len(self.restrict_to_joints) if self.restrict_to_joints is not None else 4

    @property
    def joints(self):
        return self.restrict_to_joints if self.restrict_to_joints is not None else BIOMECHANICAL_DOF_LEGEND.keys()

    def joint_row_col_index(self, joint) -> list[tuple[int, int]]:
        """Return the row and col index of the joint. ex: [(0, 0), (0, 1), (0, 2)] for glenohumeral"""
        # compute offset if limited list of joints
        count = 0
        for j in JOINT_ROW_COL_INDEX.keys():
            if j == joint:
                break
            if not j in self.joints:
                count -= 1

        return [(JOINT_ROW_COL_INDEX[joint][i][0] + count, JOINT_ROW_COL_INDEX[joint][i][1]) for i in range(3)]

    def make_fig(self, rotation: bool = True):
        return make_subplots(
            shared_xaxes=False,
            shared_yaxes=True,
            rows=self.nb_joints if self.nb_joints > 1 else 2,  # 2 rows for 1 joint because legends need space, hacky...
            cols=3,
            subplot_titles=self._rotation_titles if rotation else self._translation_titles,
        )

    @property
    def _rotation_titles(self) -> list[str]:
        suplot_titles = [list(BIOMECHANICAL_DOF_LEGEND[j]) for j in self.joints]
        return [item for sublist in suplot_titles for item in sublist]

    @property
    def _translation_titles(self) -> list[str]:
        suplot_titles = [list(TRANSLATIONAL_BIOMECHANICAL_DOF_LEGEND[j]) for j in self.joints]
        return [item for sublist in suplot_titles for item in sublist]

    def plot(self):
        # by number of data point - compute the number of rows for each article
        row_article_counts = self.dfi.df["article"].value_counts()

        for article in row_article_counts.index.to_list():
            self.showlegend = True
            self.plot_article(name=article)

    def plot_article(self, name):
        sub_dfi = DataFrameInterface(self.dfi.select_article(article=name))
        color = get_color(name)
        for j, joint in enumerate(self.joints):
            sub_df_j = sub_dfi.select_joint(joint)

            if sub_df_j.empty:
                continue

            self.plot_dofs(article=name, joint=joint, color=color)

    def plot_dofs(self, article, joint, color):
        sub_dfi = DataFrameInterface(self.dfi.select_article(article=article))
        sub_df_j = sub_dfi.select_joint(joint)

        dofs = sub_df_j["degree_of_freedom"].unique()

        for i, dof in enumerate(dofs):
            self.plot_dof(article, joint, dof, color)

    def plot_dof(self, article, joint, dof, color):
        sub_dfi = DataFrameInterface(self.dfi.select_article(article=article))
        sub_df_j = sub_dfi.select_joint(joint)
        sub_df_ij = sub_df_j[sub_df_j["degree_of_freedom"] == dof]
        row, col = self.joint_row_col_index(joint)[dof - 1]

        subjects = sub_df_ij["shoulder_id"].unique()
        nb_subjects = len(subjects)
        if nb_subjects > 1:
            for s in subjects:
                sub_df_ij_s = sub_df_ij[sub_df_ij["shoulder_id"] == s]
                self.plot_timeserie(
                    sub_df_ij_s,
                    article,
                    row,
                    col,
                    color,
                    opacity=(
                        1 if nb_subjects < 2 else self.opacity
                    ),  # NOTE: opacity is 1 if there are more than 2 subjects
                )
        else:
            self.plot_timeserie(sub_df_ij, article, row, col, color, opacity=1)

        row, col_left = self.joint_row_col_index(joint)[0]
        self.fig.update_yaxes(title_text=f"{joint[0].upper()}{joint[1:].lower()} (°)", row=row + 1, col=col_left + 1)

    def plot_timeserie(self, df, article, row, col, color, opacity):
        self.fig.add_trace(
            go.Scatter(
                x=df["humerothoracic_angle"],
                y=df["value"],
                name=AUTHOR_DISPLAYED_STUDY[article],
                # name=article,
                legendgroup=(
                    "_in_vivo" if df[self.options["marker_symbol"][0]].unique().all() else "_ex_vivo"
                ),  # todo: need a better implementation, okay for now
                legendgrouptitle=dict(
                    text=(
                        "In vivo" if df[self.options["marker_symbol"][0]].unique().all() == True else "Ex vivo"
                    ),  # todo: need a better implementation, okay for now
                    font=dict(size=14),
                ),
                showlegend=self.showlegend,
                mode=(
                    "lines+markers" if len(df["value"]) < 25 else "lines"
                ),  # NOTE: markers are not displayed if there are too many data points
                opacity=opacity,
                marker=dict(
                    size=3,
                    color=color,
                    symbol=(
                        self.options["marker_symbol"][1][0]
                        if df[self.options["marker_symbol"][0]].unique().all() == True
                        else self.options["marker_symbol"][1][1]
                    ),
                ),
                line=dict(
                    width=1.5,
                    color=color,
                ),
            ),
            row=row + 1,
            col=col + 1,
        )

        # self.fig.update_xaxes(row=row + 1, col=col + 1, range=[-150, 180])
        grid_color = "rgba(0, 0, 0, 0.1)"
        n_ticks = 8  # It doesnt seem to exactly fit the number specified
        self.fig.update_xaxes(gridcolor=grid_color, row=row + 1, col=col + 1, showgrid=True, nticks=n_ticks)
        self.fig.update_yaxes(gridcolor=grid_color, row=row + 1, col=col + 1, showgrid=True, nticks=n_ticks)
        self.showlegend = False

    def update_style(self):
        self.fig.update_layout(
            # If we fix only the height the width will be adapted to the size of the screen
            # However not fixing the height AND the width make the graph not readable
            height=self._fig_height,
            width=1000,
            paper_bgcolor="rgba(255,255,255,1)",
            plot_bgcolor="rgba(255,255,255,1)",
            legend=dict(
                title_font_family="Times New Roman",
                font=dict(family="Times New Roman", color="black", size=12),
                orientation="v",
                x=1.03,
                y=self._y_legend,
                xanchor="left",
                groupclick="togglegroup",
                # groupclick="toggleitem",  # instead of "togglegroup"
                grouptitlefont=dict(style="italic"),
                itemsizing="constant",
                indentation=5,
                tracegroupgap=1,
                traceorder="grouped",
            ),
            font=dict(
                size=14,
                family="Times New Roman",
            ),
            yaxis=dict(color="black"),
            template="simple_white",
            boxgap=0.1,
            title="<b>Shoulder kinematics</b> <br>" + f"<i>{self.dfi.motions}</i>",
            title_x=0.5,
            title_yanchor="bottom",
            title_y=self._y_title,
            title_font=dict(
                size=16,
            ),
        )

        self.fig.update_xaxes(title_text="Humerothoracic angle (°)", row=self.nb_joints, col=1)
        self.fig.update_xaxes(title_text="Humerothoracic angle (°)", row=self.nb_joints, col=2)
        self.fig.update_xaxes(title_text="Humerothoracic angle (°)", row=self.nb_joints, col=3)

        for row in range(1, self.nb_joints + 1):
            for col in range(1, 4):
                self.fig.update_xaxes(
                    showline=True, row=row, col=col, linecolor="black", linewidth=0.5, mirror=True, tickwidth=1.5
                )
                self.fig.update_yaxes(
                    showline=True,
                    row=row,
                    col=col,
                    linecolor="black",
                    linewidth=0.5,
                    mirror=True,
                    showticklabels=True,
                    tickwidth=1.5,
                )

    def show(self):
        self.fig.show()

    @property
    def _y_legend(self) -> float:
        if self.nb_joints == 1:
            return 1.1
        if self.nb_joints == 4:
            return 0.95

        return 1

    @property
    def _fig_height(self) -> int:
        return 1000 * self.nb_joints / 4 if self.nb_joints >= 3 else 600

    @property
    def _y_title(self) -> float:
        return 0.925 if self.nb_joints == 1 else 0.95
