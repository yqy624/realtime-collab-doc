class OTOperation:
    """Represents a single OT operation."""

    def __init__(self, type_: str, position: int = 0, length: int = 0,
                 content: str = "", revision: int = 0, client_id: str = ""):
        self.type = type_  # INSERT, DELETE, FULL_SYNC
        self.position = position
        self.length = length
        self.content = content or ""
        self.revision = revision
        self.client_id = client_id or ""


class OTService:
    """Operational Transformation service."""

    @staticmethod
    def apply(original: str, operation: OTOperation) -> str:
        content = original or ""
        if not operation.type:
            return content

        position = max(0, min(operation.position, len(content)))

        if operation.type == "INSERT":
            return content[:position] + operation.content + content[position:]

        elif operation.type == "DELETE":
            op_len = operation.length if operation.length else len(operation.content)
            end = min(len(content), position + max(op_len, 0))
            return content[:position] + content[end:]

        elif operation.type == "FULL_SYNC":
            return operation.content or ""

        return content

    @staticmethod
    def transform(incoming: OTOperation, applied: OTOperation) -> OTOperation:
        if not incoming.type or not applied.type:
            return incoming

        transformed = OTOperation(
            type_=incoming.type,
            position=incoming.position,
            length=incoming.length,
            content=incoming.content,
            revision=incoming.revision,
            client_id=incoming.client_id,
        )

        in_pos = max(0, transformed.position)
        ap_pos = max(0, applied.position)
        ap_len = applied.length if applied.length else len(applied.content)

        if applied.type == "INSERT":
            if in_pos > ap_pos or (incoming.type == "INSERT" and applied.type == "INSERT"
                                    and in_pos == ap_pos and (incoming.client_id or "") > (applied.client_id or "")):
                transformed.position = in_pos + ap_len
            return transformed

        if applied.type == "DELETE":
            if in_pos >= ap_pos + ap_len:
                transformed.position = max(ap_pos, in_pos - ap_len)
                return transformed

            if in_pos >= ap_pos:
                transformed.position = ap_pos
                if transformed.type == "DELETE":
                    overlap = min(ap_pos + ap_len, in_pos + (transformed.length or len(transformed.content))) - in_pos
                    transformed.length = max(0, (transformed.length or len(transformed.content)) - max(overlap, 0))

        return transformed
