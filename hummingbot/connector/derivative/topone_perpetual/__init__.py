# TopOne Perpetual 連接器
# 如果導入有問題，這個文件會防止整個模塊加載失敗
try:
    from .topone_perpetual_derivative import ToponePerpetualDerivative
    __all__ = ["ToponePerpetualDerivative"]
except ImportError as e:
    print(f"Warning: TopOne Perpetual connector import failed: {e}")
    __all__ = []