class SSEParser:
    def __init__(self):
        self.last_event_id = ""
        self.retry = None
        self.done = False
        self._line = []          # characters of the line being read
        self._skip_lf = False    # the previous character was a CR
        self._data = []          # data lines of the event being built
        self._event = ""

    def feed(self, chunk):
        out = []
        self._line, self._skip_lf = [], False
        for ch in chunk + ("\n" if chunk and chunk[-1] not in "\r\n" else ""):
            if self.done:
                break
            if self._skip_lf:
                self._skip_lf = False
                if ch == "\n":
                    continue
            if ch == "\r" or ch == "\n":
                self._skip_lf = ch == "\r"
                line = "".join(self._line)
                self._line = []
                event = self._process(line)
                if event is not None:
                    out.append(event)
            else:
                self._line.append(ch)
        return out

    def _process(self, line):
        if line == "":
            return self._dispatch()
        if line.startswith(":"):
            return None
        if ":" in line:
            field, value = line.split(":", 1)
            if value.startswith(" "):
                value = value[1:]
        else:
            field, value = line, ""
        if field == "data":
            self._data.append(value)
        elif field == "event":
            self._event = value
        elif field == "id":
            self.last_event_id = value
        elif field == "retry":
            if value.isdigit() and value.isascii():
                self.retry = int(value)
        return None

    def _dispatch(self):
        data, event_type = self._data, self._event
        self._data, self._event = [], ""
        if not data:
            return None
        text = "\n".join(data)
        if text == "[DONE]":
            self.done = True
            return None
        return {"event": event_type or "message", "data": text, "id": self.last_event_id}
