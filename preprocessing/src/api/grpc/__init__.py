"""gRPC API module."""

from .server import PreprocessingServicer, serve_grpc

__all__ = ["PreprocessingServicer", "serve_grpc"]
