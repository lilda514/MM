import asyncio
import nest_asyncio
from src.marketmaking.sharedstate import MMSharedState
from src.tools.log import LoggerInstance
import contextlib
from src.marketmaking.strat.marketmaker import TradingLogic
import traceback


async def main():
    try:
        debug = False
        rootLogger = LoggerInstance("MM",debug)
        rootLogger.setFilters("MM")
        rootLogger.setHandlers()
        ss = MMSharedState(debug=debug,logger=rootLogger)
        # trading_logic = TradingLogic(ss,rootLogger.createChild(child_name="Logic", debug_mode=debug))
        
        await asyncio.gather(
            ss.refresh_parameters(),
            ss.start_internal_processes(),
            # trading_logic.start_loop()
        )
        
    except (KeyboardInterrupt, asyncio.CancelledError):
        rootLogger.critical(f"Process manually interupted by user...")
    
    except Exception as e:
        rootLogger.critical(f"Unexpected exception occurred: {e}")
        rootLogger.critical(f"traceback: {traceback.print_tb(e.__traceback__)}")

    finally:
        rootLogger.critical("Starting shutdown sequence...")
        for exchange in ss.exchanges.keys():
            await ss.exchanges[exchange]["exchange"].shutdown()
            await ss.websockets[exchange].shutdown()
        rootLogger.info("Goodnight...")
        rootLogger.close()
        
        input("close?")

if __name__ == "__main__":
    
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    nest_asyncio.apply(loop)
    try:
        loop.run_until_complete(main())
    finally:
        try:
            all_tasks = asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True)
            all_tasks.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                loop.run_until_complete(all_tasks)
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()

# import asyncio
# import nest_asyncio
# from src.marketmaking.sharedstate import MMSharedState
# from src.tools.log import LoggerInstance

# async def shutdown(loop, rootLogger, ss):
#     print("Starting shutdown sequence...")

#     # Cancel all running tasks
#     tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
#     for task in tasks:
#         task.cancel()
#         try:
#             await task
#         except asyncio.CancelledError:
#             pass

#     for exchange in ss.exchanges.keys():
#         await ss.exchanges[exchange]["exchange"].shutdown()
#         await ss.websockets[exchange].shutdown()

#     rootLogger.info("Goodnight...")
#     rootLogger.close()
#     input("close?")

# async def main():
#     rootLogger = LoggerInstance("MM", True)
#     ss = MMSharedState(True, rootLogger)
    
#     try:
#         await asyncio.gather(
#             ss.refresh_parameters(),
#             ss.start_internal_processes(),
#         )
#     except asyncio.CancelledError:
#         rootLogger.critical("Process manually interrupted by user...")
#     except Exception as e:
#         rootLogger.critical(f"Unexpected exception occurred: {e}")
#     finally:
#         await shutdown(asyncio.get_event_loop(), rootLogger, ss)

# def handle_exit(loop, rootLogger, ss):
#     for task in asyncio.all_tasks(loop=loop):
#         task.cancel()
#     asyncio.create_task(shutdown(loop, rootLogger, ss))

# if __name__ == "__main__":
#     loop = asyncio.get_event_loop()
#     nest_asyncio.apply(loop)
#     rootLogger = LoggerInstance("MM", True)
#     ss = MMSharedState(True, rootLogger)

#     try:
#         # Run the main function until complete or until an exception occurs
#         loop.run_until_complete(main())
#     except (KeyboardInterrupt, asyncio.CancelledError):
#         handle_exit(loop, rootLogger, ss)
#     finally:
#         try:
#             loop.run_until_complete(shutdown(loop, rootLogger, ss))
#         except RuntimeError:
#             pass  # Loop is already closed
#         loop.close()

# rootLogger = LoggerInstance("MM",True)
# rootLogger.setFilters("MM")
# rootLogger.setHandlers()
# ss = MMSharedState(True,rootLogger)
