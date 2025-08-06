"""
設定保存・読み込み管理モジュール
複数の設定プロファイルを管理できるシステム
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from auto_mosaic.src.utils import get_app_data_dir, ProcessingConfig
import logging

logger = logging.getLogger(__name__)

class ConfigProfile:
    """設定プロファイル"""
    
    def __init__(self, name: str, config_data: Dict[str, Any], description: str = ""):
        self.name = name
        self.description = description
        self.config_data = config_data
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "description": self.description,
            "config_data": self.config_data,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigProfile':
        """辞書から復元"""
        profile = cls(data["name"], data["config_data"], data.get("description", ""))
        profile.created_at = data.get("created_at", datetime.now().isoformat())
        profile.modified_at = data.get("modified_at", datetime.now().isoformat())
        return profile
    
    def update_config(self, config_data: Dict[str, Any]):
        """設定を更新"""
        self.config_data = config_data
        self.modified_at = datetime.now().isoformat()

class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self):
        self.app_data_dir = Path(get_app_data_dir())
        self.config_dir = self.app_data_dir / "config" / "profiles"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # プロファイル管理ファイル
        self.profiles_file = self.config_dir / "profiles.json"
        
        # デフォルト設定ファイル
        self.default_config_file = self.config_dir / "default.json"
        
        # プロファイル一覧
        self.profiles: Dict[str, ConfigProfile] = {}
        self.current_profile_name: Optional[str] = None
        
        # 起動時に既存の設定を読み込み
        self._load_profiles()
    
    def processing_config_to_dict(self, config: ProcessingConfig) -> Dict[str, Any]:
        """ProcessingConfigオブジェクトを辞書に変換"""
        return {
            # 基本設定
            "strength": config.strength,
            "feather": config.feather,
            "confidence": config.confidence,
            "visualize": config.visualize,
            "bbox_expansion": config.bbox_expansion,
            
            # モザイク設定
            "use_fanza_standard": config.use_fanza_standard,
            "manual_tile_size": config.manual_tile_size,
            "mosaic_types": config.mosaic_types,
            "gaussian_blur_radius": config.gaussian_blur_radius,
            
            # デバイス設定
            "device_mode": config.device_mode,
            
            # モデル選択
            "selected_models": config.selected_models,
            
            # SAM設定
            "sam_use_vit_b": config.sam_use_vit_b,
            "sam_use_none": config.sam_use_none,
            
            # 処理モード
            "use_seamless": config.use_seamless,
            "use_legacy": config.use_legacy,
            
            # ファイル名設定
            "filename_mode": config.filename_mode,
            "filename_prefix": config.filename_prefix,
            "sequential_prefix": config.sequential_prefix,
            "sequential_start_number": config.sequential_start_number,
            
            # 個別拡張設定
            "use_individual_expansion": config.use_individual_expansion,
            "individual_expansions": config.individual_expansions,
            
            # 検出器設定
            "detector_mode": config.detector_mode,
            "use_anime_detector": config.use_anime_detector,
            "use_nudenet": config.use_nudenet,
            
            # カスタムモデル設定
            "use_custom_models": config.use_custom_models,
            "custom_models": config.custom_models,
            
            # 実写検出専用範囲調整設定
            "use_nudenet_shrink": config.use_nudenet_shrink,
            "nudenet_shrink_values": config.nudenet_shrink_values,
        }
    
    def dict_to_processing_config(self, config_dict: Dict[str, Any]) -> ProcessingConfig:
        """辞書からProcessingConfigオブジェクトを復元"""
        config = ProcessingConfig()
        
        # 設定値を復元（存在しない場合はデフォルト値を使用）
        config.strength = config_dict.get("strength", config.strength)
        config.feather = config_dict.get("feather", config.feather)
        config.confidence = config_dict.get("confidence", config.confidence)
        config.visualize = config_dict.get("visualize", config.visualize)
        config.bbox_expansion = config_dict.get("bbox_expansion", config.bbox_expansion)
        
        config.use_fanza_standard = config_dict.get("use_fanza_standard", config.use_fanza_standard)
        config.manual_tile_size = config_dict.get("manual_tile_size", config.manual_tile_size)
        config.mosaic_types = config_dict.get("mosaic_types", config.mosaic_types)
        config.gaussian_blur_radius = config_dict.get("gaussian_blur_radius", config.gaussian_blur_radius)
        
        config.device_mode = config_dict.get("device_mode", config.device_mode)
        config.selected_models = config_dict.get("selected_models", config.selected_models)
        
        config.sam_use_vit_b = config_dict.get("sam_use_vit_b", config.sam_use_vit_b)
        config.sam_use_none = config_dict.get("sam_use_none", config.sam_use_none)
        
        config.use_seamless = config_dict.get("use_seamless", config.use_seamless)
        config.use_legacy = config_dict.get("use_legacy", config.use_legacy)
        
        config.filename_mode = config_dict.get("filename_mode", config.filename_mode)
        config.filename_prefix = config_dict.get("filename_prefix", config.filename_prefix)
        config.sequential_prefix = config_dict.get("sequential_prefix", config.sequential_prefix)
        config.sequential_start_number = config_dict.get("sequential_start_number", config.sequential_start_number)
        
        config.use_individual_expansion = config_dict.get("use_individual_expansion", config.use_individual_expansion)
        config.individual_expansions = config_dict.get("individual_expansions", config.individual_expansions)
        
        config.detector_mode = config_dict.get("detector_mode", config.detector_mode)
        config.use_anime_detector = config_dict.get("use_anime_detector", config.use_anime_detector)
        config.use_nudenet = config_dict.get("use_nudenet", config.use_nudenet)
        
        config.use_custom_models = config_dict.get("use_custom_models", config.use_custom_models)
        config.custom_models = config_dict.get("custom_models", config.custom_models)
        
        # 実写検出専用範囲調整設定
        config.use_nudenet_shrink = config_dict.get("use_nudenet_shrink", config.use_nudenet_shrink)
        config.nudenet_shrink_values = config_dict.get("nudenet_shrink_values", config.nudenet_shrink_values)
        
        return config
    
    def save_profile(self, name: str, config: ProcessingConfig, description: str = "") -> bool:
        """設定プロファイルを保存"""
        try:
            config_dict = self.processing_config_to_dict(config)
            
            if name in self.profiles:
                # 既存プロファイルを更新
                self.profiles[name].update_config(config_dict)
                if description:
                    self.profiles[name].description = description
            else:
                # 新規プロファイル作成
                self.profiles[name] = ConfigProfile(name, config_dict, description)
            
            self._save_profiles()
            logger.info(f"設定プロファイル '{name}' を保存しました")
            return True
            
        except Exception as e:
            logger.error(f"設定プロファイル '{name}' の保存に失敗: {e}")
            return False
    
    def load_profile(self, name: str) -> Optional[ProcessingConfig]:
        """設定プロファイルを読み込み"""
        try:
            if name not in self.profiles:
                logger.warning(f"設定プロファイル '{name}' が見つかりません")
                return None
            
            profile = self.profiles[name]
            config = self.dict_to_processing_config(profile.config_data)
            self.current_profile_name = name
            
            logger.info(f"設定プロファイル '{name}' を読み込みました")
            return config
            
        except Exception as e:
            logger.error(f"設定プロファイル '{name}' の読み込みに失敗: {e}")
            return None
    
    def delete_profile(self, name: str) -> bool:
        """設定プロファイルを削除"""
        try:
            if name not in self.profiles:
                logger.warning(f"設定プロファイル '{name}' が見つかりません")
                return False
            
            del self.profiles[name]
            
            # 現在のプロファイルが削除された場合はリセット
            if self.current_profile_name == name:
                self.current_profile_name = None
            
            self._save_profiles()
            logger.info(f"設定プロファイル '{name}' を削除しました")
            return True
            
        except Exception as e:
            logger.error(f"設定プロファイル '{name}' の削除に失敗: {e}")
            return False
    
    def get_profile_list(self) -> List[Dict[str, Any]]:
        """プロファイル一覧を取得"""
        return [
            {
                "name": profile.name,
                "description": profile.description,
                "created_at": profile.created_at,
                "modified_at": profile.modified_at,
                "is_current": profile.name == self.current_profile_name
            }
            for profile in self.profiles.values()
        ]
    
    def save_as_default(self, config: ProcessingConfig) -> bool:
        """現在の設定をデフォルトとして保存"""
        try:
            config_dict = self.processing_config_to_dict(config)
            
            with open(self.default_config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "config": config_dict,
                    "saved_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            logger.info("デフォルト設定を保存しました")
            return True
            
        except Exception as e:
            logger.error(f"デフォルト設定の保存に失敗: {e}")
            return False
    
    def load_default(self) -> Optional[ProcessingConfig]:
        """デフォルト設定を読み込み"""
        try:
            if not self.default_config_file.exists():
                logger.info("デフォルト設定ファイルが見つかりません")
                return None
            
            with open(self.default_config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            config = self.dict_to_processing_config(data["config"])
            self.current_profile_name = None
            
            logger.info("デフォルト設定を読み込みました")
            return config
            
        except Exception as e:
            logger.error(f"デフォルト設定の読み込みに失敗: {e}")
            return None
    
    def _save_profiles(self):
        """プロファイル一覧をファイルに保存"""
        try:
            profiles_data = {
                "profiles": {name: profile.to_dict() for name, profile in self.profiles.items()},
                "current_profile": self.current_profile_name,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(profiles_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"プロファイル一覧の保存に失敗: {e}")
    
    def _load_profiles(self):
        """プロファイル一覧をファイルから読み込み"""
        try:
            if not self.profiles_file.exists():
                logger.info("プロファイル一覧ファイルが見つかりません。新規作成します。")
                return
            
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # プロファイルを復元
            for name, profile_data in data.get("profiles", {}).items():
                self.profiles[name] = ConfigProfile.from_dict(profile_data)
            
            self.current_profile_name = data.get("current_profile")
            
            logger.info(f"{len(self.profiles)}個の設定プロファイルを読み込みました")
            
        except Exception as e:
            logger.error(f"プロファイル一覧の読み込みに失敗: {e}")
            self.profiles = {}
            self.current_profile_name = None
    
    def export_profile(self, name: str, export_path: str) -> bool:
        """プロファイルをファイルにエクスポート"""
        try:
            if name not in self.profiles:
                logger.warning(f"設定プロファイル '{name}' が見つかりません")
                return False
            
            profile = self.profiles[name]
            export_data = {
                "auto_mosaic_config_export": True,
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "profile": profile.to_dict()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"設定プロファイル '{name}' を {export_path} にエクスポートしました")
            return True
            
        except Exception as e:
            logger.error(f"設定プロファイル '{name}' のエクスポートに失敗: {e}")
            return False
    
    def import_profile(self, import_path: str) -> Optional[str]:
        """プロファイルをファイルからインポート"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # ファイル形式チェック
            if not data.get("auto_mosaic_config_export"):
                logger.error("不正な設定ファイル形式です")
                return None
            
            profile_data = data["profile"]
            original_name = profile_data["name"]
            
            # 重複チェック（重複する場合は名前を変更）
            name = original_name
            counter = 1
            while name in self.profiles:
                name = f"{original_name}_{counter}"
                counter += 1
            
            # プロファイルを作成
            profile = ConfigProfile.from_dict(profile_data)
            profile.name = name  # 重複回避後の名前に変更
            self.profiles[name] = profile
            
            self._save_profiles()
            logger.info(f"設定プロファイル '{name}' をインポートしました")
            return name
            
        except Exception as e:
            logger.error(f"設定プロファイルのインポートに失敗: {e}")
            return None