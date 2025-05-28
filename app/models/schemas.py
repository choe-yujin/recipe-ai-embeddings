from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# OCR 관련 스키마
class OCRResponse(BaseModel):
    ingredients: List['RecognizedIngredient']
    confidence: float = Field(..., ge=0, le=1)
    processing_time: float

class RecognizedIngredient(BaseModel):
    original_text: str
    matched_id: Optional[str]
    matched_name: Optional[str]
    confidence: float = Field(..., ge=0, le=1)
    alternatives: List[str] = []

# 레시피 추천 관련 스키마
class RecommendationRequest(BaseModel):
    ingredients: List[str]
    limit: int = Field(default=10, ge=1, le=50)
    user_id: Optional[str]

class RecipeScore(BaseModel):
    recipe_id: str
    name: str
    score: float
    match_reason: str
    ingredients: List[str]
    cooking_method: Optional[str]
    category: Optional[str]

class RecommendationResponse(BaseModel):
    recipes: List[RecipeScore]
    total_matches: int
    processing_time: float

# 날씨 기반 추천 관련 스키마
class WeatherData(BaseModel):
    temperature: float
    condition: str
    humidity: int
    feels_like: float
    location: str
    timestamp: datetime

class SeasonalIngredient(BaseModel):
    name: str
    category: str
    season: str
    confidence: float = Field(..., ge=0, le=1)

class WeatherRecommendationRequest(BaseModel):
    location: str
    user_id: Optional[str]
    limit: int = Field(default=10, ge=1, le=50)

class WeatherRecommendationResponse(BaseModel):
    weather: WeatherData
    seasonal_ingredients: List[SeasonalIngredient]
    recipes: List[RecipeScore]
    recommendation_reason: str
    processing_time: float

# 에러 응답 스키마
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str]
    code: str 