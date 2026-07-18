"""
موتور مسیریابی. فقط از یال‌هایی استفاده می‌کنه که is_operational=True باشن -
یعنی خط ریلی واقعاً فعاله، نه پروژه‌ی در دست ساخت (مثل کریدور کاشغر-اوش
که تا نوشتن این کد هنوز کامل نشده). اگر مسیر عملیاتی پیدا نشه، به‌جای
حدس زدن، صادقانه می‌گه "مسیر ریلی مستقیم/کامل ثبت‌شده‌ای نداریم".

الگوریتم: Dijkstra ساده با heapq (بدون وابستگی خارجی مثل networkx).
برای مسیر جایگزین: پرهزینه‌ترین یال مسیر اصلی رو موقتاً حذف می‌کنه و
دوباره مسیر پیدا می‌کنه (یک روش استاندارد و ساده برای k-امین مسیر کوتاه).
"""
import heapq
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from database.models import Station, RailConnection


@dataclass
class RoutePath:
    stations: List[Station]
    total_distance_km: Optional[float]
    corridors: List[str]


def _build_graph(db: Session) -> Dict[int, List[Tuple[int, float, int]]]:
    """گراف مجاورت: station_id -> [(neighbor_id, distance, connection_id), ...]"""
    graph: Dict[int, List[Tuple[int, float, int]]] = {}
    edges = db.query(RailConnection).filter(RailConnection.is_operational.is_(True)).all()
    for e in edges:
        dist = e.distance_km if e.distance_km is not None else 1.0
        graph.setdefault(e.from_station_id, []).append((e.to_station_id, dist, e.id))
        graph.setdefault(e.to_station_id, []).append((e.from_station_id, dist, e.id))  # دوطرفه
    return graph


def _dijkstra(graph, start_id: int, end_id: int, banned_edge_ids=frozenset()):
    dist = {start_id: 0.0}
    prev = {}
    prev_edge = {}
    pq = [(0.0, start_id)]
    visited = set()

    while pq:
        d, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        if node == end_id:
            break
        for neighbor, weight, edge_id in graph.get(node, []):
            if edge_id in banned_edge_ids:
                continue
            nd = d + weight
            if neighbor not in dist or nd < dist[neighbor]:
                dist[neighbor] = nd
                prev[neighbor] = node
                prev_edge[neighbor] = edge_id
                heapq.heappush(pq, (nd, neighbor))

    if end_id not in dist:
        return None, None, None

    path = [end_id]
    edge_ids = []
    node = end_id
    while node != start_id:
        edge_ids.append(prev_edge[node])
        node = prev[node]
        path.append(node)
    path.reverse()
    edge_ids.reverse()
    return path, dist[end_id], edge_ids


def find_routes(
    db: Session, origin: Station, destination: Station
) -> Tuple[Optional[RoutePath], Optional[RoutePath]]:
    """برمی‌گردونه: (مسیر اصلی, مسیر جایگزین) - هرکدوم ممکنه None باشه اگه پیدا نشه"""
    graph = _build_graph(db)

    main_path_ids, main_dist, main_edges = _dijkstra(graph, origin.id, destination.id)
    if main_path_ids is None:
        return None, None

    stations_by_id = {s.id: s for s in db.query(Station).filter(Station.id.in_(main_path_ids)).all()}
    corridors = [
        c.corridor_name for c in db.query(RailConnection).filter(RailConnection.id.in_(main_edges)).all()
        if c.corridor_name
    ]
    main_route = RoutePath(
        stations=[stations_by_id[i] for i in main_path_ids],
        total_distance_km=main_dist,
        corridors=list(dict.fromkeys(corridors)),  # حذف تکراری با حفظ ترتیب
    )

    # مسیر جایگزین: طولانی‌ترین یال مسیر اصلی رو ببند و دوباره جستجو کن
    alt_route = None
    if main_edges:
        banned = frozenset([main_edges[0]])  # ساده: اولین یال رو می‌بندیم
        alt_path_ids, alt_dist, alt_edges = _dijkstra(graph, origin.id, destination.id, banned)
        if alt_path_ids and alt_path_ids != main_path_ids:
            alt_stations = {s.id: s for s in db.query(Station).filter(Station.id.in_(alt_path_ids)).all()}
            alt_corridors = [
                c.corridor_name for c in db.query(RailConnection).filter(RailConnection.id.in_(alt_edges)).all()
                if c.corridor_name
            ]
            alt_route = RoutePath(
                stations=[alt_stations[i] for i in alt_path_ids],
                total_distance_km=alt_dist,
                corridors=list(dict.fromkeys(alt_corridors)),
            )

    return main_route, alt_route
