## Data Privacy and Terms of Service Compliance

### Understanding the Risk

This MCP server enables AI assistants to query Synapse biomedical datasets using your personal access token. However, the [Synapse Terms of Service](https://www.synapse.org/TrustCenter:TermsOfService) explicitly prohibit redistribution of Synapse data.

When you use this server with external, cloud-based AI models:
1. Your queries and Synapse's responses are sent to the AI provider
2. The AI provider may store, log, or process this data
3. This storage could be interpreted as unauthorized redistribution under Synapse ToS

### Compliant Usage Scenarios

✅ **Safe to use:**
- Enterprise AI deployments with contractual data protection guarantees
- Self-hosted or local AI models (e.g., Ollama, LM Studio)
- Environments where you control data retention and the data is not redistributed

❌ **Use with caution:**
- Consumer cloud AI services (Claude, ChatGPT, Gemini, etc.) that may store conversations
- Any service without explicit guarantees that your data will not be retained or redistributed

### Your Responsibility

By using this MCP server, you acknowledge that:
- You are responsible for compliance with Synapse Terms of Service
- You will ensure any AI service you connect meets Synapse's data handling requirements
- You will use appropriate enterprise or self-hosted solutions if required by your data governance obligations

For questions about acceptable use, please consult the [Synapse Terms of Service](https://www.synapse.org/TrustCenter:TermsOfService) or contact Synapse support.
