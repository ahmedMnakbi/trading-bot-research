# Pre-Live Governance

Governance exists to keep live trading, real orders, and private API access disabled until a separate future process explicitly designs and reviews those capabilities.

Human approval is mandatory before any real-money deployment. Task 8 still forbids live trading and does not add any authenticated connector.

Before any future real connector could be considered, the project would need documented approval, tested safety controls, operational monitoring, incident procedures, key management, and explicit human sign-off.

Approval metadata alone must not enable live trading. In Task 8, `live_trading_allowed`, `real_orders_allowed`, and `private_api_allowed` must remain false.

