"""Supabase table access. Route handlers do not call the client directly."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from app.errors import IntegrationError, NotFoundError
from app.utils.time import utc_now


def _data(response: Any) -> list[dict]:
    return list(response.data or [])


def _first(response: Any, message: str) -> dict:
    rows = _data(response)
    if not rows:
        raise NotFoundError(message)
    return rows[0]


class RecordsRepository:
    def __init__(self, client: Any) -> None:
        self.client = client

    def _run(self, action: str, func):
        try:
            return func()
        except NotFoundError:
            raise
        except Exception as exc:
            raise IntegrationError(f"Database {action} failed.") from exc

    def create_location(self, payload: dict) -> dict:
        def action():
            return self.client.table("locations").insert(payload).execute()

        return _first(self._run("insert location", action), "Location was not saved.")

    def list_locations(self) -> list[dict]:
        def action():
            return (
                self.client.table("locations")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )

        return _data(self._run("list locations", action))

    def get_location(self, location_id: UUID) -> dict:
        def action():
            return (
                self.client.table("locations")
                .select("*")
                .eq("id", str(location_id))
                .limit(1)
                .execute()
            )

        return _first(self._run("read location", action), "Location not found.")

    def create_crop(self, payload: dict) -> dict:
        def action():
            return self.client.table("crop_records").insert(payload).execute()

        return self.get_crop(UUID(_first(self._run("insert crop", action), "Crop was not saved.")["id"]))

    def list_crops(self, location_id: UUID | None = None) -> list[dict]:
        def action():
            query = self.client.table("crop_records").select(
                "*, locations(name, state, district)"
            )
            if location_id is not None:
                query = query.eq("location_id", str(location_id))
            return query.order("created_at", desc=True).execute()

        return [_with_location_name(row) for row in _data(self._run("list crops", action))]

    def get_crop(self, crop_id: UUID) -> dict:
        def action():
            return (
                self.client.table("crop_records")
                .select("*, locations(name, state, district)")
                .eq("id", str(crop_id))
                .limit(1)
                .execute()
            )

        return _with_location_name(
            _first(self._run("read crop", action), "Crop not found.")
        )

    def update_crop(self, crop_id: UUID, payload: dict) -> dict:
        def action():
            return (
                self.client.table("crop_records")
                .update(payload)
                .eq("id", str(crop_id))
                .execute()
            )

        self._run("update crop", action)
        return self.get_crop(crop_id)

    def delete_crop(self, crop_id: UUID) -> None:
        self.get_crop(crop_id)

        def action():
            return self.client.table("crop_records").delete().eq("id", str(crop_id)).execute()

        self._run("delete crop", action)

    def create_environment(self, payload: dict) -> dict:
        def action():
            return self.client.table("environmental_records").insert(payload).execute()

        return _first(
            self._run("insert environmental record", action),
            "Environmental record was not saved.",
        )

    def list_environment(
        self,
        location_id: UUID | None = None,
        crop_id: UUID | None = None,
        limit: int = 50,
    ) -> list[dict]:
        def action():
            query = self.client.table("environmental_records").select("*")
            if location_id is not None:
                query = query.eq("location_id", str(location_id))
            if crop_id is not None:
                query = query.eq("crop_id", str(crop_id))
            return query.order("recorded_at", desc=True).limit(limit).execute()

        return _data(self._run("list environmental records", action))

    def create_advisory(self, payload: dict) -> dict:
        def action():
            return self.client.table("advisory_records").insert(payload).execute()

        return _first(self._run("insert advisory", action), "Advisory was not saved.")

    def list_advisories(
        self,
        crop_id: UUID | None = None,
        advisory_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
    ) -> list[dict]:
        def action():
            query = self.client.table("advisory_records").select("*")
            if crop_id is not None:
                query = query.eq("crop_id", str(crop_id))
            if advisory_type:
                query = query.eq("advisory_type", advisory_type)
            if date_from is not None:
                query = query.gte("created_at", date_from.isoformat())
            if date_to is not None:
                query = query.lte("created_at", date_to.isoformat())
            return query.order("created_at", desc=True).limit(limit).execute()

        return _data(self._run("list advisories", action))

    def get_advisory(self, advisory_id: UUID) -> dict:
        def action():
            return (
                self.client.table("advisory_records")
                .select("*")
                .eq("id", str(advisory_id))
                .limit(1)
                .execute()
            )

        return _first(self._run("read advisory", action), "Advisory not found.")

    def recent_advisories(self, crop_id: UUID, limit: int = 3) -> list[dict]:
        return self.list_advisories(crop_id=crop_id, limit=limit)

    def add_chat_message(self, payload: dict) -> dict:
        def action():
            return self.client.table("chat_messages").insert(payload).execute()

        return _first(self._run("insert chat message", action), "Chat message was not saved.")

    def list_chat(self, conversation_id: UUID) -> list[dict]:
        def action():
            return (
                self.client.table("chat_messages")
                .select("*")
                .eq("conversation_id", str(conversation_id))
                .order("created_at")
                .execute()
            )

        return _data(self._run("list chat messages", action))

    def create_alert(self, payload: dict) -> dict:
        def action():
            return self.client.table("alerts").insert(payload).execute()

        return _first(self._run("insert alert", action), "Alert was not saved.")

    def list_alerts(
        self,
        crop_id: UUID | None = None,
        location_id: UUID | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        def action():
            query = self.client.table("alerts").select("*")
            if crop_id is not None:
                query = query.eq("crop_id", str(crop_id))
            if location_id is not None:
                query = query.eq("location_id", str(location_id))
            if unread_only:
                query = query.eq("is_read", False)
            return query.order("created_at", desc=True).limit(limit).execute()

        return _data(self._run("list alerts", action))

    def mark_alert_read(self, alert_id: UUID) -> dict:
        def action():
            return (
                self.client.table("alerts")
                .update({"is_read": True})
                .eq("id", str(alert_id))
                .execute()
            )

        rows = _data(self._run("update alert", action))
        if not rows:
            raise NotFoundError("Alert not found.")
        return rows[0]

    def find_recent_alert(
        self,
        category: str,
        location_id: UUID | None,
        crop_id: UUID | None,
        within_hours: int,
    ) -> dict | None:
        since = utc_now() - timedelta(hours=within_hours)

        def action():
            query = (
                self.client.table("alerts")
                .select("*")
                .eq("category", category)
                .eq("is_read", False)
                .gte("created_at", since.isoformat())
            )
            if location_id is None:
                query = query.is_("location_id", "null")
            else:
                query = query.eq("location_id", str(location_id))
            if crop_id is None:
                query = query.is_("crop_id", "null")
            else:
                query = query.eq("crop_id", str(crop_id))
            return query.limit(1).execute()

        rows = _data(self._run("find recent alert", action))
        return rows[0] if rows else None

    def create_document(self, payload: dict) -> dict:
        def action():
            return self.client.table("knowledge_documents").insert(payload).execute()

        return _first(self._run("insert document", action), "Document was not saved.")

    def update_document(self, document_id: UUID, payload: dict) -> dict:
        def action():
            return (
                self.client.table("knowledge_documents")
                .update(payload)
                .eq("id", str(document_id))
                .execute()
            )

        rows = _data(self._run("update document", action))
        if not rows:
            raise NotFoundError("Knowledge document not found.")
        return rows[0]

    def list_documents(self) -> list[dict]:
        def action():
            return (
                self.client.table("knowledge_documents")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )

        return _data(self._run("list documents", action))

    def get_document(self, document_id: UUID) -> dict:
        def action():
            return (
                self.client.table("knowledge_documents")
                .select("*")
                .eq("id", str(document_id))
                .limit(1)
                .execute()
            )

        return _first(self._run("read document", action), "Knowledge document not found.")

    def delete_document(self, document_id: UUID) -> dict:
        document = self.get_document(document_id)

        def action():
            return (
                self.client.table("knowledge_documents")
                .delete()
                .eq("id", str(document_id))
                .execute()
            )

        self._run("delete document", action)
        return document

    def insert_chunks(self, rows: list[dict]) -> None:
        if not rows:
            return

        def action():
            return self.client.table("knowledge_chunks").insert(rows).execute()

        self._run("insert knowledge chunks", action)

    def match_chunks(
        self,
        embedding: list[float],
        match_count: int,
        crop: str | None,
        region: str | None,
        disease: str | None,
    ) -> list[dict]:
        def action():
            return self.client.rpc(
                "match_knowledge_chunks",
                {
                    "query_embedding": _vector_literal(embedding),
                    "match_count": match_count,
                    "filter_crop": crop,
                    "filter_region": region,
                    "filter_disease": disease,
                },
            ).execute()

        return _data(self._run("search knowledge", action))

    def upload_document_file(self, path: str, content: bytes, content_type: str) -> None:
        def action():
            return self.client.storage.from_("knowledge-documents").upload(
                path,
                content,
                file_options={"content-type": content_type, "upsert": "true"},
            )

        self._run("upload document", action)

    def remove_document_file(self, path: str) -> None:
        def action():
            return self.client.storage.from_("knowledge-documents").remove([path])

        try:
            self._run("remove document file", action)
        except IntegrationError:
            return


def _with_location_name(row: dict) -> dict:
    location = row.get("locations")
    if isinstance(location, dict):
        row["location_name"] = location.get("name")
    return row


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
