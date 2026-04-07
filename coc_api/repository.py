import json
import sqlite3
from pathlib import Path

from .parsers import (
    BATTLE_CATEGORY_KEYS,
    BattleBuckets,
    empty_battle_buckets,
    parse_stored_battle,
)
from .utils import normalize_player_tag


class BattleLogRepository:
    def __init__(self, db_path: Path, category_limit: int) -> None:
        self.db_path = db_path
        self.category_limit = category_limit

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _create_tracked_battles_table(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tracked_battles (
                player_tag TEXT NOT NULL,
                battle_hash TEXT NOT NULL,
                category TEXT NOT NULL,
                battle_json TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                first_seen_order INTEGER NOT NULL,
                last_seen_at TEXT NOT NULL,
                PRIMARY KEY (player_tag, battle_hash)
            );

            DROP INDEX IF EXISTS idx_tracked_battles_player_category_recency;
            CREATE INDEX IF NOT EXISTS idx_tracked_battles_player_category_recency
            ON tracked_battles (
                player_tag,
                category,
                first_seen_at DESC,
                first_seen_order DESC
            );
            """
        )

    def init_db(self) -> None:
        with self._get_connection() as connection:
            self._create_tracked_battles_table(connection)

    def purge_untracked_players(self, tracked_tags: tuple[str, ...]) -> None:
        with self._get_connection() as connection:
            if tracked_tags:
                placeholders = ",".join("?" for _ in tracked_tags)
                connection.execute(
                    f"""
                    DELETE FROM tracked_battles
                    WHERE player_tag NOT IN ({placeholders})
                    """,
                    tracked_tags,
                )
            else:
                connection.execute("DELETE FROM tracked_battles")

            connection.commit()

    def store_battle_views(
        self,
        player_tag: str,
        battle_buckets: BattleBuckets,
        seen_at: str,
    ) -> None:
        normalized_tag = normalize_player_tag(player_tag)

        with self._get_connection() as connection:
            for category in BATTLE_CATEGORY_KEYS:
                battles = battle_buckets.get(category, [])

                for first_seen_order, battle in enumerate(battles):
                    if not isinstance(battle, dict):
                        continue

                    connection.execute(
                        """
                        INSERT INTO tracked_battles (
                            player_tag,
                            battle_hash,
                            category,
                            battle_json,
                            first_seen_at,
                            first_seen_order,
                            last_seen_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(player_tag, battle_hash) DO UPDATE SET
                            category = excluded.category,
                            battle_json = excluded.battle_json,
                            last_seen_at = excluded.last_seen_at
                        """,
                        (
                            normalized_tag,
                            str(battle.get("hash", "")),
                            category,
                            json.dumps(
                                battle,
                                separators=(",", ":"),
                                ensure_ascii=False,
                            ),
                            seen_at,
                            first_seen_order,
                            seen_at,
                        ),
                    )

                connection.execute(
                    """
                    DELETE FROM tracked_battles
                    WHERE player_tag = ?
                      AND category = ?
                      AND battle_hash NOT IN (
                          SELECT battle_hash
                          FROM tracked_battles
                          WHERE player_tag = ?
                            AND category = ?
                          ORDER BY first_seen_at DESC, first_seen_order DESC
                          LIMIT ?
                      )
                    """,
                    (
                        normalized_tag,
                        category,
                        normalized_tag,
                        category,
                        self.category_limit,
                    ),
                )

            connection.commit()

    def get_stored_battle_log(self, tag: str) -> BattleBuckets:
        normalized_tag = normalize_player_tag(tag)
        buckets = empty_battle_buckets()

        with self._get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    category,
                    battle_hash,
                    battle_json
                FROM tracked_battles
                WHERE player_tag = ?
                ORDER BY category, first_seen_at ASC, first_seen_order ASC
                """,
                (normalized_tag,),
            ).fetchall()

        for row in rows:
            category = row["category"]
            if category not in buckets:
                continue

            buckets[category].append(
                parse_stored_battle(row["battle_json"], row["battle_hash"])
            )

        return buckets

    def get_stored_battle_counts(self, tag: str) -> dict[str, int]:
        stored = self.get_stored_battle_log(tag)
        return {category: len(battles) for category, battles in stored.items()}
