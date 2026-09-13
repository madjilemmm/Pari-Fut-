"""Database integrity tests against the real PostgreSQL instance."""
from sqlalchemy import text

from backend.db.connection import engine


def test_matches_table_has_real_data():
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
    assert count > 1000  # 4 real PL seasons


def test_no_duplicate_matches_in_db():
    with engine.connect() as conn:
        dupes = conn.execute(text("""
            SELECT home_team_id, away_team_id, kickoff_utc, COUNT(*)
            FROM matches
            GROUP BY home_team_id, away_team_id, kickoff_utc
            HAVING COUNT(*) > 1
        """)).fetchall()
    assert len(dupes) == 0


def test_prediction_before_kickoff_trigger_blocks_future_timestamp():
    """The DB trigger must reject a prediction generated after kickoff."""
    from datetime import timedelta, timezone
    import uuid

    with engine.connect() as conn:
        match_id, kickoff = conn.execute(text(
            "SELECT match_id, kickoff_utc FROM matches ORDER BY kickoff_utc LIMIT 1"
        )).first()
        model_version_id = conn.execute(text(
            "SELECT model_version_id FROM model_versions LIMIT 1"
        )).scalar()

        # Unique as_of per test run so re-runs never collide on the unique constraint.
        as_of = kickoff.replace(tzinfo=timezone.utc) - timedelta(seconds=1)
        snap_id = conn.execute(text("""
            INSERT INTO feature_snapshots (match_id, as_of, features)
            VALUES (:match_id, :as_of, :features) RETURNING id
        """), {"match_id": match_id, "as_of": as_of, "features": f'{{"test_run": "{uuid.uuid4()}"}}'}).scalar()
        conn.commit()

        raised_after = False
        try:
            conn.execute(text("""
                INSERT INTO predictions (match_id, model_version_id, feature_snapshot_id,
                    prediction_type, generated_at, home_win_prob, draw_prob, away_win_prob,
                    home_xg, away_xg)
                VALUES (:match_id, :mv_id, :snap_id, 'H-1', :after_kickoff, 0.4, 0.3, 0.3, 1.0, 1.0)
            """), {
                "match_id": match_id, "mv_id": model_version_id, "snap_id": snap_id,
                "after_kickoff": kickoff + timedelta(hours=1),
            })
            conn.commit()
        except Exception:
            raised_after = True
            conn.rollback()
        finally:
            with engine.connect() as cleanup_conn:
                cleanup_conn.execute(text("DELETE FROM feature_snapshots WHERE id = :id"), {"id": snap_id})
                cleanup_conn.commit()

    assert raised_after, "Trigger should have rejected a prediction generated after kickoff"
