from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from pydantic import BaseModel
from typing import List, Optional
import json

app = FastAPI(
    title="YouTube 字幕 API",
    description="一个用于下载 YouTube 视频字幕的 API 服务",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境中应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscriptResponse(BaseModel):
    video_id: str
    language: str
    transcript: List[dict]

class LanguageInfo(BaseModel):
    language: str
    language_code: str
    is_generated: bool

class LanguagesResponse(BaseModel):
    video_id: str
    available_languages: List[LanguageInfo]

@app.get("/", tags=["根"])
async def root():
    return {"message": "欢迎使用 YouTube 字幕 API"}

@app.get("/api/transcript/{video_id}", response_model=TranscriptResponse, tags=["字幕"])
async def get_transcript(video_id: str, language: Optional[str] = None):
    """
    获取指定 YouTube 视频的字幕
    
    - **video_id**: YouTube 视频 ID
    - **language**: 可选，指定字幕语言代码 (例如: 'en', 'zh-CN')
    """
    try:
        if language:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
            lang = language
        else:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            lang = "auto"
        
        return {
            "video_id": video_id,
            "language": lang,
            "transcript": transcript
        }
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise HTTPException(status_code=404, detail=f"找不到字幕: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取字幕时出错: {str(e)}")

@app.get("/api/languages/{video_id}", response_model=LanguagesResponse, tags=["字幕"])
async def get_available_languages(video_id: str):
    """
    获取指定 YouTube 视频可用的字幕语言列表
    
    - **video_id**: YouTube 视频 ID
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        languages = []
        
        for transcript in transcript_list:
            languages.append({
                "language": transcript.language,
                "language_code": transcript.language_code,
                "is_generated": transcript.is_generated
            })
        
        return {
            "video_id": video_id,
            "available_languages": languages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取可用语言时出错: {str(e)}")

@app.get("/api/srt/{video_id}", tags=["字幕"])
async def get_srt_format(video_id: str, language: Optional[str] = None):
    """
    获取 SRT 格式的字幕
    
    - **video_id**: YouTube 视频 ID
    - **language**: 可选，指定字幕语言代码
    """
    try:
        if language:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        else:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        srt_content = convert_to_srt(transcript)
        return {"video_id": video_id, "srt_content": srt_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 SRT 格式字幕时出错: {str(e)}")

def convert_to_srt(transcript):
    """将字幕转换为 SRT 格式"""
    srt_content = ""
    for i, segment in enumerate(transcript, 1):
        start_time = format_time(segment['start'])
        end_time = format_time(segment['start'] + segment['duration'])
        text = segment['text']
        
        srt_content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
    
    return srt_content

def format_time(seconds):
    """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)