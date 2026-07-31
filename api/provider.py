from api.jiosaavn import Jiosaavn
from api.youtube import YouTube


class Provider:

    def __init__(self):
        self.jiosaavn = Jiosaavn()
        self.youtube = YouTube()

    # ==========================
    # SEARCH
    # ==========================

    async def search(
        self,
        query: str,
        source: str = "auto",
        limit: int = 10
    ):

        if source == "jiosaavn":
            return await self.jiosaavn.search(
                query=query,
                search_type="songs",
                page_size=limit
            )

        if source == "youtube":
            return await self.youtube.search(
                query=query,
                limit=limit
            )

        # AUTO MODE
        try:
            result = await self.jiosaavn.search(
                query=query,
                search_type="songs",
                page_size=limit
            )

            if (
                result
                and result.get("results")
            ):
                return result

        except Exception:
            pass

        return await self.youtube.search(
            query=query,
            limit=limit
        )

    # ==========================
    # SONG DETAILS
    # ==========================

    async def get_song(
        self,
        item_id: str,
        source: str
    ):

        if source == "jiosaavn":
            return await self.jiosaavn.get_song(item_id)

        return await self.youtube.get_info(item_id)