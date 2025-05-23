import os
import io
import zipfile
from fastapi.responses import StreamingResponse

def zip_stream(filenames: list[str]) -> StreamingResponse:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as temp_zip:
        for path in filenames:
            _, name = os.path.split(path)
            temp_zip.write(path, name)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), 
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=all_html_files.zip"}
    )
