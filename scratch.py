import json
from datetime import datetime

from cluster import Cluster
from conference import Conference
from defs import FBS, PFIVE, GFIVE
from team import Team


def load_schedule():
    with open("schedule.json", "r", encoding='utf8') as file:
        global schedule
        schedule = json.load(file)


def make_cluster_graphs(absolute=False, old=None, scale=None, week=-1):
    groups = {'fbs': FBS, 'pfive': PFIVE, 'gfive': GFIVE, 'independent': ['independent']}
    for cluster in groups:
        current = Cluster(schedule=schedule,
                          teams=[x for x in schedule if schedule[x]['conference'] in groups[cluster]])
        if not scale:
            for color in ['team', 'red-green', 'red-blue']:
                current.make_standings_projection_graph(method='sp+', absolute=absolute, old=old, file=cluster,
                                                        scale=color, week=week)
        else:
            current.make_standings_projection_graph(method='sp+', absolute=absolute, old=old, file=cluster, scale=scale,
                                                    week=week)


def make_conf_graphs(absolute=False, old=None, scale=None, week=-1):
    for conference in PFIVE + GFIVE:
        conf = Conference(name=conference, schedule=schedule)
        if not scale:
            for color in ['team', 'red-green', 'red-blue']:
                try:
                    conf.make_standings_projection_graph(absolute=absolute, method='sp+', file=conference, old=old,
                                                         scale=color, week=week)
                except KeyError:
                    print('problem with {}'.format(conf))
        else:
            try:
                conf.make_standings_projection_graph(absolute=absolute, method='sp+', file=conference, old=old,
                                                     scale=scale, week=week)
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
#groups = {'fbs': FBS, 'pfive': PFIVE, 'gfive': GFIVE, 'independent': ['independent']}
#current = Cluster(schedule=schedule, teams=[x for x in schedule if schedule[x]['conference'] in FBS])
#current.rank_schedules(spplus=current.get_avg_spplus(0, 25), txtoutput=True)
#current.make_schedule_ranking_graph(spplus='top25')

make_conf_graphs(old=True, week=4)
make_cluster_graphs(old=True, week=4)
make_team_graphs(old=True, week=4)
