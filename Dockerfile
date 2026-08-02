FROM python:3.11-slim

WORKDIR /app

# Environment Variables
ENV API_ID=31812858
ENV API_HASH=037d80c792f88251f405447fe195cc59
ENV BOT_TOKEN=your_new_bot_token_here
ENV DATABASE_URL=sqlite:///jiosaavn.db
ENV PYTHONUNBUFFERED=1

# 🔥 Ye Cookies Set Karo (Netscape Format Wala)
ENV YOUTUBE_COOKIES="# Netscape HTTP Cookie File\n# https://curl.haxx.se/rfc/cookie_spec.html\n# This is a generated file! Do not edit.\n\n.youtube.com\tTRUE\t/\tTRUE\t1801054490\t__Secure-YNID\t20.YT=Qt9JnCO_s3FgNeoJ7OfDgmd5eh78x1pDVu23mfuEOlna4I5L6lwkhbwUN6iLFxC98-PYxjcNoXNZ78KJw5pjzjgPtLp5IPnPpUVE3ggXniba2nrXQePjHozbHyR3n5zkDI962NAjNbydFLaluApyyAi-8-788Z36oCPXAeVTZKUQiOlDBUBgobxNgZNL9CES2Khm862ptVYunCevh6KkaRmXYUDsa3ZHLiTCKx_TogkPdCD0DxLNNsZqgfEfCovN1H9m5keHOLUcZhrX5wEhnc3Ma71bXbgjtY9Gof9T27FXk3fpd2st5tsI_4TqN9KIrNPHmZ5URxaKioUwCU8Ycw\n.youtube.com\tTRUE\t/\tTRUE\t1784265328\tGPS\t1\n.youtube.com\tTRUE\t/\tTRUE\t1801054541\tVISITOR_INFO1_LIVE\tGQ9M6cDYI1w\n.youtube.com\tTRUE\t/\tTRUE\t1801054541\tVISITOR_PRIVACY_METADATA\tCgJJThIEGgAgGg%3D%3D\n.youtube.com\tTRUE\t/\tTRUE\t1820062542\tPREF\ttz=Asia.Kolkata\n.youtube.com\tTRUE\t/\tTRUE\t1817038540\t__Secure-1PSIDTS\tsidts-CjUBPWEu2VJ2gm5OPLXJXYcPwqgrHgdqDMk7UUCw8AoqwbzWKBRZQeWNPWbcxkSdyqmws93ELBAA\n.youtube.com\tTRUE\t/\tTRUE\t1817038540\t__Secure-3PSIDTS\tsidts-CjUBPWEu2VJ2gm5OPLXJXYcPwqgrHgdqDMk7UUCw8AoqwbzWKBRZQeWNPWbcxkSdyqmws93ELBAA\n.youtube.com\tTRUE\t/\tFALSE\t1820062541\tHSID\tAZY0cCidjO9R-WefO\n.youtube.com\tTRUE\t/\tTRUE\t1820062541\tSSID\tA07ZBS6lEywDb4kx-\n.youtube.com\tTRUE\t/\tFALSE\t1820062541\tAPISID\tDzzwIf8MbHqI_D-4/AYc83b2-EZtzPHczx\n.youtube.com\tTRUE\t/\tTRUE\t1820062541\tSAPISID\t-ToKv-qARJbGdur6/AC8R-z-hVUtVulFBa\n.youtube.com\tTRUE\t/\tTRUE\t1820062541\t__Secure-1PAPISID\t-ToKv-qARJbGdur6/AC8R-z-hVUtVulFBa\n.youtube.com\tTRUE\t/\tTRUE\t1820062541\t__Secure-3PAPISID\t-ToKv-qARJbGdur6/AC8R-z-hVUtVulFBa\n.youtube.com\tTRUE\t/\tFALSE\t1820062541\tSID\tg.a000BAmZchTHB81SKgLopleQESFDcVmipSrpMCCFoHJ5H6Uo9j5vsp_LUZ6-kQ1m66P7DXsiXQACgYKAUwSARUSFQHGX2MivDHSDHcO6f_arsGbW1wBPhoVAUF8yKp59xra-xnjGPa9yM4I_q1h0076\n.youtube.com\tTRUE\t/\tTRUE\t1820062541\t__Secure-1PSID\tg.a000BAmZchTHB81SKgLopleQESFDcVmipSrpMCCFoHJ5H6Uo9j5vHrL6hD4fmd12HEhXVONv1wACgYKAaESARUSFQHGX2Mi6ZX2jWDzWOh9PwUWv_WQ_hoVAUF8yKpu_CiqoUwyo3U4xY0MNIvC0076\n.youtube.com\tTRUE\t/\tTRUE\t1820062541\t__Secure-3PSID\tg.a000BAmZchTHB81SKgLopleQESFDcVmipSrpMCCFoHJ5H6Uo9j5vtztid2X8hdBA4vriNF_GUQACgYKAVESARUSFQHGX2Mi9sR0nDubNtepJE1g4G8AnRoVAUF8yKr-SKZVMDUA6EKb26DaekvT0076\n.youtube.com\tTRUE\t/\tFALSE\t1817038545\tSIDCC\tAKEyXzXT3YJT0UoqUiEWITtAzzqVXiPsF0y4aDXcWZTOdxTIdEtTXAwknle3nE43RP-dIoC4\n.youtube.com\tTRUE\t/\tTRUE\t1817038545\t__Secure-1PSIDCC\tAKEyXzXexLSgjBhws--0inCXwJDQVnmhCxhEYVJ3nq7bzQwOrIJNAQ-3aXWZYVBT6e_yTL_x\n.youtube.com\tTRUE\t/\tTRUE\t1817038545\t__Secure-3PSIDCC\tAKEyXzWYvtlsuWautABlR_5cfozdpxfgeHnswXqTfvGGAHCYUd3ee-P6hXEnLZL8pnbYj74FzQ\n.youtube.com\tTRUE\t/\tTRUE\t1820062541\tLOGIN_INFO\tAFmmF2swRQIhAJDfoz9d_vLQw7WUGazDXcXf6oeXsfjRkpc_N7imwSz1AiB2XpH5Bt5Azy6ppYWpI4k3GPvh1U26cNMqPB3YK_A6lA:QUQ3MjNmeWFQa19xamdqTTZnNVJneFdrQk50enhMYjRYekQ0eGw0VVJUUHpUUFh1X0pYR3BaU1Z2MWZFNXRfc0VBRDhRY3A2SGk0NkRnRGVJVWYwUXJPYlV5cHFOQXozWFJMNmpzRjlnUmFGYUN1WHlmVXZUYy0xVHpTS21KRF9Hakh0OTZvX2o0dHVkd01ITUFlTmZabjNad0stYXJlSGJR\n.youtube.com\tTRUE\t/\tTRUE\t0\tYSC\tKgqpHiDKlHs\n.youtube.com\tTRUE\t/\tFALSE\t1785502506\tST-16vjsij\tcsn=L46k7ZfZITcrLngU&itct=CBQQ-I8FGAEiEwjiuImN-_yVAxWWsykDHXo_M-syDGF0b20tYWNjb3VudMoBBOnrlXo%3D"

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-m", "jiosaavn"]