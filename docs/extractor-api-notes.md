# Extractor API Notes

Based on reading `extractor.py` (copied from `script.py`):

1. **Start the session**: The provided script does not contain a main session loop or `client.run()`. It only defines utility classes. Therefore, the wrapper will need to instantiate `TikTokLiveClient(unique_id=username)` itself.
2. **Events/callbacks**: The script imports `CommentEvent`, `ConnectEvent`, `DisconnectEvent` from `TikTokLive`. The wrapper should use `@client.on(CommentEvent)` to receive comments.
3. **Comment object shape**: The `CommentData` class in the script expects:
   ```python
   commenter: str
   live_host: str
   comment: str
   phones: List[str]
   timestamp: str
   ```
   The wrapper will yield a custom `Comment` BaseModel as per ADR-002:
   ```python
   class Comment(BaseModel):
       author: str
       text: str
       timestamp: datetime
   ```
4. **Phone extraction**: `PhoneExtractor.extract(text: str) -> List[str]` is a synchronous class method that returns a list of Nepali phone numbers.
5. **Stop/Disconnect**: `TikTokLiveClient` provides a `stop()` or `disconnect()` method. The wrapper will need to listen for the Temporal `stop()` signal and call `client.stop()`.

The wrapper will:
- Initialize `TikTokLiveClient(username)`
- Register a handler for `CommentEvent` that puts events into an `asyncio.Queue`
- Run the client in an async task
- Yield comments from the queue until stopped
