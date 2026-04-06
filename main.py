import asyncio
import logging
import aio_pika
from faststream import FastStream
from app.config.settings import settings
from faststream.rabbit import RabbitBroker, RabbitQueue, ExchangeType, RabbitExchange

from app.schema.camera import CameraScheme
from app.services.stream_manager import stream_manager


# Настройка логирования
logging.basicConfig(level=logging.INFO)


queue_add_camera = RabbitQueue("add_camera", auto_delete=False, routing_key="camera.add.*")
queue_remove_camera = RabbitQueue("remove_camera", auto_delete=False, routing_key="camera.remove.*")
queue_update_camera = RabbitQueue("update_camera", auto_delete=False, routing_key="camera.update.*")

exchange = RabbitExchange(settings.CAMERA_EXCHANGE_NAME, ExchangeType.TOPIC, auto_delete=False)

broker = RabbitBroker(url=settings.rabbitmq_url)
app = FastStream(broker)


@broker.subscriber(queue_add_camera, exchange)
async def camera_add_handler(camera: CameraScheme):
    logging.info(f"STREAM ADD {camera}")

    base = settings.media_server_rtsp_base_url.rstrip("/")
    output_url = f"{base}/{camera.id}"
    
    stream_manager.add_stream(
        source_uri=camera.rtsp_url,
        output_url=output_url,
        stream_id=camera.id,
    )

    if camera.rtsp_url_preview is not None:
        output_url_preview = f"{base}/{camera.id}_p"
        stream_manager.add_stream(
            source_uri=camera.rtsp_url_preview,
            output_url=output_url_preview,
            stream_id=f"{camera.id}_p",
        )

@broker.subscriber(queue_remove_camera, exchange)
async def camera_remove_handler(camera: CameraScheme):
    logging.info(f"STREAM REMOVE {camera}")
    stream_manager.remove_stream(stream_id=camera.id)
    if camera.rtsp_url_preview is not None:
        stream_manager.remove_stream(stream_id=f"{camera.id}_p")


@broker.subscriber(queue_update_camera, exchange)
async def camera_update_handler(camera: CameraScheme):
    logging.info(f"STREAM UPDATE {camera}")

    stream_manager.remove_stream(stream_id=camera.id)
    if camera.rtsp_url_preview is not None:
        stream_manager.remove_stream(stream_id=f"{camera.id}_p")
    await asyncio.sleep(1)

    base = settings.media_server_rtsp_base_url.rstrip("/")
    output_url = f"{base}/{camera.id}"

    stream_manager.add_stream(
        source_uri=camera.rtsp_url,
        output_url=output_url,
        stream_id=camera.id,
    )
    if camera.rtsp_url_preview is not None:
        output_url_preview = f"{base}/{camera.id}_p"
        stream_manager.add_stream(
            source_uri=camera.rtsp_url_preview,
            output_url=output_url_preview,
            stream_id=f"{camera.id}_p",
        )


async def main():
    async with broker:
        camera_add_queue: aio_pika.RobustQueue = await broker.declare_queue(queue_add_camera)
        camera_remove_queue: aio_pika.RobustQueue = await broker.declare_queue(queue_remove_camera)
        camera_update_queue: aio_pika.RobustQueue = await broker.declare_queue(queue_update_camera)

        camera_exchange: aio_pika.RobustExchange = await broker.declare_exchange(exchange)

        await camera_add_queue.bind(exchange=camera_exchange)
        await camera_remove_queue.bind(exchange=camera_exchange)
        await camera_update_queue.bind(exchange=camera_exchange)

    logging.info("App started")
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
