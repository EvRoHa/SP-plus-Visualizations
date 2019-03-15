import os

from graph import Graph
from team import Team
from utils import Utils


class Conference:
    def __init__(self, name, schedule):
        self.name = name
        self.teams = {Team(name=x, schedule=schedule) for x in schedule if schedule[x]['conference'] == name}
        self.divisions = {}
        for team in self.teams:
            if team.division not in self.divisions:
                self.divisions[team.division] = []
            self.divisions[team.division].append(team)

        if len(self.divisions) == 0:
            self.divisions['all'] = self.teams

    def get_record_array(self, week=-1, order='winexp'):
        # get the records for the final week for each team
        record = []

        for t in self.teams:
            record.append([t, t.project_win_totals(week=week)[-1], t.project_win_totals(week=week - 1)[-1]])

        # sort teams by their weighted average number of wins and division
        if order == 'winexp':
            record.sort(key=lambda x: (x[0].division, sum([x[1][z] * z for z in range(len(x[1]))])), reverse=True)
        elif order == 'sp+':
            record.sort(key=lambda x: (x[0].division, x[0].latest_spplus), reverse=True)
        new = [x[0].name for x in record]
        if order == 'winexp':
            last = sorted(record, key=lambda x: (x[0].division, sum([x[2][z] * z for z in range(len(x[2]))])), reverse=True)
        elif order == 'sp+':
            last = sorted(record, key=lambda x: (x[0].division, sum([x[2][z] * z for z in range(len(x[2]))])),
                          reverse=True)
        # find the team's last divisional rank
        last = [x[0].name for x in last]
        div_size = len(list(self.divisions.items())[0][1])
        for i in range(len(last)):
            for y in record:
                if last[i] == y[0].name:
                    new_rank = new.index(last[i]) % div_size + 1
                    old_rank = i % div_size + 1
                    y.append([new_rank, old_rank, old_rank - new_rank])
        return record

    def make_standings_projection_graph(self, file='out', week=None, hstep=50, vstep=50, margin=5, logowidth=40,
                                        method='sp+', logoheight=40, absolute=False,
                                        scale='red-green', old=None, order='winexp'):

        # get the records for the final week for each team
        record = self.get_record_array(week=week, order=order)

        if not os.path.exists(".\svg output\{} ~ {}".format(method, scale)):
            os.makedirs(".\svg output\{} ~ {}".format(method, scale))
        path = os.path.join(".\svg output\{} ~ {}".format(method, scale),
                            '{} ~ {} ~ {} using {}.svg'.format(file, method, scale, order))

        if not old:
            rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 1
        else:
            rows, cols = len(record) + 2, max([len(x[1]) for x in record]) + 3

        graph = Graph(path=path, width=hstep * cols + 2 * margin, height=vstep * rows + 2 * margin)

        # Add the horizontal header label; it is at the very top of the svg and covers the win columns, with centered text
        graph.add_text(margin + hstep * (cols / 2), margin + vstep * 0.5 - 4, size=13, alignment='middle',
                       text='Total Wins as projected by {} ordered by {}'.format(method.upper(), order.upper()))

        if not week or week == 0:
            first_week = 0
        else:
            first_week = week - 1

        # Add the horizontal header label; it is at the very top of the svg and covers all but the first column, with centered text
        graph.add_text(margin + hstep * (cols / 2),
                       margin + vstep * 0.5 + 9,
                       size=13, alignment='middle',
                       text='(change after week {} games)'.format(first_week))

        # Add column labels for the Team Name
        graph.add_text(margin + hstep * 0.5, margin + vstep * 1.5, alignment='middle', size=13, text='Team')

        # This set of loops fills in the body of the table
        for i in range(0, rows - 2):
            # Add the team logo
            graph.add_image(margin + (hstep - logowidth) / 2,
                            vstep * (2 + i) + margin + (vstep - logoheight) / 2,
                            logowidth,
                            logoheight,
                            record[i][0].logo_URI)

            # find the max and min in this week to determine color of cell
            if absolute:
                upper, lower = 1, 0
            else:
                upper, lower = max(record[i][1]), min(record[i][1])

            for j in range(0, cols - 1):
                if i == 0:
                    if j == cols - 3:
                        if old:
                            # Add the column label
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5 - 10,
                                           size=10,
                                           alignment='middle',
                                           text='Expected')
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5,
                                           size=10,
                                           alignment='middle',
                                           text='Wins')
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5 + 10,
                                           alignment='middle',
                                           size=10,
                                           text='(Change)')
                    elif j == cols - 2:
                        if old:
                            # Add the column label
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5 - 10,
                                           size=10,
                                           alignment='middle',
                                           text='Divisional')
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5,
                                           size=10,
                                           alignment='middle',
                                           text='Rank')
                            graph.add_text(margin + hstep * (1.5 + j),
                                           margin + vstep * 1.5 + 10,
                                           alignment='middle',
                                           size=10,
                                           text='(Change)')
                    else:
                        if j != 1:
                            txt = 'Wins'
                        else:
                            txt = 'Win'

                        # Add the column label
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5 - 7,
                                       size=13,
                                       alignment='middle',
                                       text=j)
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * 1.5 + 7,
                                       size=13,
                                       alignment='middle',
                                       text=txt)

                if j < len(record[i][1]):
                    if absolute:
                        r, g, b = Utils.gradient_color(0, 1, record[i][1][j], scale=scale,
                                                       primaryColor=record[i][0].primary_color,
                                                       secondaryColor=record[i][0].secondary_color)
                    else:
                        r, g, b = Utils.gradient_color(lower, upper, record[i][1][j], scale=scale,
                                                       primaryColor=record[i][0].primary_color,
                                                       secondaryColor=record[i][0].secondary_color)

                    # Draw the color-coded box
                    graph.add_rect(margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep,
                                   color='none', fill=(r, g, b))

                    # Should the text be white or black?
                    text_color = Utils.get_text_contrast_color(r, g, b)

                    # Write the probability in the box
                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i) - 2,
                                   alignment='middle',
                                   color=tuple(text_color),
                                   text=str(round(100 * record[i][1][j], 1)) + '%')

                    # Add the cumulative probability text
                    graph.add_text(0.8 * margin + hstep * (2 + j),
                                   vstep * (3 + i),
                                   alignment='middle', anchor='end', size=8,
                                   color=tuple(text_color),
                                   text=str(round(abs(100 * (1 - sum(record[i][1][x] for x in range(0, j)))), 1)) + '%')

                    if old:
                        diff = round(100 * (record[i][1][j] - record[i][2][j]), 1)
                        if diff > 0:
                            txt = '(+{})%'.format(diff)
                        elif diff < 0:
                            txt = '(' + str(diff) + '%)'
                        else:
                            txt = '(+' + str(diff) + '%)'

                        # Write the probability change in the box
                        graph.add_text(margin + hstep * (1.5 + j),
                                       margin + vstep * (2.5 + i) + 8,
                                       size=10, alignment='middle',
                                       color=tuple(text_color),
                                       text=txt)

                elif j == cols - 3 and old:
                    # Calculate the win expectation
                    old_xw = sum(x * record[i][2][x] for x in range(len(record[i][2])))
                    new_xw = sum(x * record[i][1][x] for x in range(len(record[i][1])))
                    diff = round(new_xw - old_xw, 1)
                    if diff > 0:
                        txt = '(+{})'.format(diff)
                        r, g, b = 0, 205, 0
                        weight = 'bolder'
                    elif diff < 0:
                        txt = '(' + str(diff) + ')'
                        r, g, b = 255, 77, 77
                        weight = 'bolder'
                    else:
                        txt = '(+0.0)'
                        r, g, b = 0, 0, 0
                        weight = 'normal'

                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i) - 2,
                                   size=13,
                                   text=round(new_xw, 1))

                    # How did the win expectation change?
                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i) + 8,
                                   alignment='middle',
                                   size=10,
                                   color=(r, g, b),
                                   weight=weight,
                                   text=txt)
                elif j == cols - 2 and old:
                    # Calculate the divisional rank
                    diff = record[i][3][2]
                    if diff > 0:
                        txt = '(+{})'.format(diff)
                        r, g, b = 0, 205, 0
                        weight = 'bolder'
                    elif diff < 0:
                        txt = '(' + str(diff) + ')'
                        r, g, b = 255, 77, 77
                        weight = 'bolder'
                    else:
                        txt = '(-)'
                        r, g, b = 0, 0, 0
                        weight = 'normal'

                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i) - 2,
                                   size=13,
                                   text=record[i][3][0])

                    # How did the divisional rank change?
                    graph.add_text(margin + hstep * (1.5 + j),
                                   margin + vstep * (2.5 + i) + 8,
                                   alignment='middle',
                                   size=10,
                                   color=(r, g, b),
                                   weight=weight,
                                   text=txt)
                else:
                    # Draw the color-coded box
                    graph.add_rect(margin + hstep * (1 + j), margin + vstep * (2 + i), hstep, vstep,
                                   color='none', fill=(150, 150, 150))

        # This set of loops draws the grid over the table.
        for i in range(2, rows):
            for j in range(1, cols):
                # add the vertical lines between the columns
                graph.add_line(x1=margin + hstep * j, y1=margin + vstep, x2=margin + hstep * j,
                               y2=margin + vstep * rows)

                # add the horizontal lines between the rows
                graph.add_line(x1=margin, y1=margin + vstep * i, x2=margin + hstep * cols,
                               y2=margin + vstep * i)

        # add the horizontal line between the divisions
        graph.add_line(x1=margin, y1=margin + vstep * (2 + len(self.teams) / len(self.divisions)),
                       x2=margin + hstep * cols, y2=margin + vstep * (2 + len(self.teams) / len(self.divisions)),
                       width=3)

        # Draw the outline box for the table
        graph.add_rect(margin, margin + vstep, hstep * cols, vstep * (rows - 1), color=(0, 0, 0), fill='none',
                       stroke_width=2)

        # Draw the outline box for the win total sub-table
        graph.add_rect(margin + hstep, margin + vstep, hstep * (cols - 1), vstep * (rows - 1), color=(0, 0, 0),
                       fill='none', stroke_width=2)

        # Draw the outline box for the column headers
        graph.add_rect(margin, margin + vstep, hstep * cols, vstep, color=(0, 0, 0), fill='none', stroke_width=2)

        # Draw the outline box for the win total header label
        graph.add_rect(margin + hstep, margin, hstep * (cols - 3), vstep, color=(0, 0, 0), fill='none', stroke_width=2)
        graph.write_file()
