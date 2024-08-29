"""A map reader for postgresql, conforming to
the interface defined in openlr_dereferencer.maps.abstract"""

from typing import Iterable, Optional
from openlr import Coordinates
from .primitives import Line, Node, ExampleMapError
from openlr_dereferencer.maps import MapReader


class PostgresMapReader(MapReader):
    """
    This is a reader for the basemap table stored in postgres as two tables of lines and nodes`.
    """

    def __init__(
        self,
        db_schema,
        lines_tbl_name,
        nodes_tbl_name,
        conn,
        srid=4326,
    ):
        self.db_schema = db_schema
        self.lines_tbl_name = lines_tbl_name
        self.nodes_tbl_name = nodes_tbl_name
        self.connection = conn
        self.srid = srid

    def __enter__(self):
        self.cursor = self.connection.cursor() if self.connection else None
        return self

    def __exit__(self, *exc_info):
        # make sure the cursor gets closed
        try:
            close_it = self.cursor.close
        except AttributeError:
            pass
        else:
            close_it()

    def get_line(self, line_id: int) -> Line:
        # Just verify that this line ID exists.
        self.cursor.execute(
            f"SELECT line_id FROM {self.db_schema}.{self.lines_tbl_name} WHERE line_id=%s",
            (line_id,),
        )
        if self.cursor.fetchone() is None:
            raise ExampleMapError(f"The line {line_id} does not exist")
        return Line(self, line_id)

    def get_lines(self) -> Iterable[Line]:
        self.cursor.execute(
            f"SELECT line_id FROM {self.db_schema}.{self.lines_tbl_name}"
        )
        for (line_id,) in self.cursor.fetchall():
            yield Line(self, line_id)

    def get_linecount(self) -> int:
        self.cursor.execute(
            f"SELECT COUNT(*) FROM {self.db_schema}.{self.lines_tbl_name}"
        )
        (count,) = self.cursor.fetchone()
        return count

    def get_node(self, node_id: int) -> Node:
        self.cursor.execute(
            f"SELECT node_id FROM {self.db_schema}.{self.nodes_tbl_name} WHERE node_id=%s",
            (node_id,),
        )
        (node_id,) = self.cursor.fetchone()
        return Node(self, node_id)

    def get_nodes(self) -> Iterable[Node]:
        self.cursor.execute(
            f"SELECT node_id FROM {self.db_schema}.{self.nodes_tbl_name}"
        )
        for (node_id,) in self.cursor.fetchall():
            yield Node(self, node_id)

    def get_nodecount(self) -> int:
        self.cursor.execute(
            f"SELECT COUNT(*) FROM {self.db_schema}.{self.nodes_tbl_name}"
        )
        (count,) = self.cursor.fetchone()
        return count

    def find_nodes_close_to(
        self, coord: Coordinates, dist: float
    ) -> Iterable[Node]:
        """Finds all nodes in a given radius, given in meters
        Yields every node within this distance to `coord`."""
        lon, lat = coord.lon, coord.lat
        stmt = f"""
            SELECT
                node_id
            FROM {self.db_schema}.{self.nodes_tbl_name}
            WHERE ST_DWithin(
                ST_SetSRID(ST_MakePoint(%s,%s), {self.srid}),
                geometry,
                %s
            );
        """
        self.cursor.execute(stmt, (lon, lat, dist))
        for (node_id,) in self.cursor.fetchall():
            yield Node(self, node_id)

    def find_lines_close_to(
        self,
        coord: Coordinates,
        dist: float,
        and_filter_str: Optional[str] = "",
    ) -> Iterable[Line]:
        "Yields all lines within `dist` meters around `coord`"
        lon, lat = coord.lon, coord.lat
        stmt = f"""
            SELECT
                line_id
            FROM {self.db_schema}.{self.lines_tbl_name} 
            WHERE ST_DWithin(
                ST_SetSRID(ST_MakePoint(%s,%s), {self.srid}),
                geometry,
                %s
            )
            {and_filter_str}
            ;
        """
        self.cursor.execute(stmt, (lon, lat, dist))
        for (line_id,) in self.cursor.fetchall():
            yield Line(self, line_id)
