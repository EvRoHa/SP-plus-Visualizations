import json

from cluster import Cluster
from conference import Conference
from defs import FBS, PFIVE, GFIVE
from team import Team


def load_schedule():
    with open("schedule.json", "r", encoding='utf8') as file:
        global schedule
        schedule = json.load(file)


def make_cluster_graphs(absolute=False, old=None, scale=None, week=-1, order='winexp'):
    groups = {'fbs': FBS, 'pfive': PFIVE, 'gfive': GFIVE, 'independent': ['independent']}
    for cluster in groups:
        current = Cluster(schedule=schedule,
                          teams=[x for x in schedule if schedule[x]['conference'] in groups[cluster]])
        if not scale:
            for color in ['team', 'red-green', 'red-blue']:
                current.make_standings_projection_graph(method='sp+', absolute=absolute, old=old, file=cluster,
                                                        scale=color, week=week, order=order)
        else:
            current.make_standings_projection_graph(method='sp+', absolute=absolute, old=old, file=cluster, scale=scale,
                                                    week=week, order=order)


def make_conf_graphs(absolute=False, old=None, scale=None, week=-1, order='winexp'):
    for conference in PFIVE + GFIVE:
        conf = Conference(name=conference, schedule=schedule)
        if not scale:
            for color in ['team', 'red-green', 'red-blue']:
                try:
                    conf.make_standings_projection_graph(absolute=absolute, method='sp+', file=conference, old=old,
                                                         scale=color, week=week, order=order)
                except KeyError:
                    print('problem with {}'.format(conf))
        else:
            try:
                conf.make_standings_projection_graph(absolute=absolute, method='sp+', file=conference, old=old,
                                                     scale=scale, week=week, order=order)
            except KeyError:
                print('problem with {}'.format(conf))


def make_team_graphs(old=True, scale=None, week=-1):
    for team in schedule:
        if schedule[team]['conference'] in FBS:
            val = Team(name=team, schedule=schedule)
            if not scale:
                for color in ['team', 'red-green', 'red-blue']:
                    val.make_win_probability_graph(absolute=False, file=team, old=old, scale=color, method='sp+',
                                                   week=week)
            else:
                val.make_win_probability_graph(absolute=False, file=team, old=old, scale=scale, method='sp+')


load_schedule()

groups = {'fbs': FBS, 'pfive': PFIVE, 'gfive': GFIVE, 'independent': ['independent']}
current = Cluster(schedule=schedule, teams=[x for x in schedule if schedule[x]['conference'] in FBS])
current.write_expected_win_csv()

current.rank_schedules(spplus=current.get_avg_spplus(0, 25), txtoutput=True)
current.make_schedule_ranking_graph(spplus='top5')
current.make_schedule_ranking_graph(spplus='average')

make_conf_graphs(old=True, week=13, order='sp+')
make_conf_graphs(old=True, week=13, order='winexp')
make_cluster_graphs(old=True, week=13, order='sp+')
make_cluster_graphs(old=True, week=13, order='winexp')
make_team_graphs(old=True, week=13)
