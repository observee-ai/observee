/**
 * Simple MCP agent with Anthropic and tool filtering enabled by default
 */

import { ChatAnthropic } from '@langchain/anthropic';
import * as dotenv from 'dotenv';
import { LangChainAdapter } from '../adapters/langchain-adapter.js';
import { BaseLLMProvider, PROVIDERS } from '../providers/index.js';
import { BaseToolFilter, createFilter } from '../search/index.js';
import {
  AgentConfig,
  ChatResponse,
  ChatWithToolsResponse,
  LLMProvider,
  MCPConfig,
  Message,
  StreamChunk,
  ToolResult
} from '../types.js';
import { MCPClientWrapper } from '../utils/mcp-client.js';
// import { ChatGoogleGenerativeAI } from '@langchain/google-genai';
import { AIMessage, HumanMessage, SystemMessage } from '@langchain/core/messages';
import { ChatPromptTemplate, MessagesPlaceholder } from '@langchain/core/prompts';
import { ChatGoogleGenerativeAI } from '@langchain/google-genai';
import { ChatOpenAI } from '@langchain/openai';
import { AgentExecutor, createOpenAIToolsAgent, createToolCallingAgent } from 'langchain/agents';

dotenv.config();

export class MCPAgent {
  private serverName: string;
  private authToken?: string;
  private serverUrl: string;
  private enableFiltering: boolean;
  private mcp: MCPClientWrapper;
  private toolFilter?: BaseToolFilter;
  private vectorStoreManager?: any;
  private provider!: BaseLLMProvider;
  private providerName!: string;
  private model: string;
  private allTools: any[] = [];
  private messages: Message[] = [];

  constructor(config: AgentConfig) {
    const {
      provider = 'anthropic',
      serverName = 'observee',
      model,
      serverUrl,
      syncTools = true,
      filterType,
      enableFiltering = true,
      authToken,
      ...providerKwargs
    } = config;

    // Server configuration
    this.serverName = serverName;
    this.authToken = authToken;

    if (!serverUrl) {
      throw new Error('serverUrl is required. Please provide the MCP server URL.');
    }
    this.serverUrl = serverUrl;

    // Create MCP client config
    const mcpConfig: MCPConfig = {
      mcpServers: {
        [serverName]: { url: this.serverUrl }
      }
    };

    // Add headers if auth token is provided
    if (authToken) {
      mcpConfig.mcpServers[serverName].headers = {
        'X-API-Key': authToken
      };
    }

    // Initialize MCP client wrapper
    this.mcp = new MCPClientWrapper(mcpConfig);

    // Store filtering configuration
    this.enableFiltering = enableFiltering;

    // Initialize tool filter only if filtering is enabled
    if (enableFiltering) {
      const filter = filterType || 'bm25';

      // Initialize vector store manager for cloud filters
      if (filter === 'cloud') {
        // TODO: Implement cloud vector store
        console.warn('Cloud filter not yet implemented, falling back to BM25');
      }

      // Create tool filter
      this.toolFilter = createFilter(filter, this.vectorStoreManager, syncTools);
      this.toolFilter.setServerInfo(serverName, serverUrl);

      console.info(`Using ${filter} filter for tool search`);
    } else {
      console.info('Tool filtering disabled - using native MCP');
    }

    // Initialize LLM provider
    this.initializeProvider(provider, model, providerKwargs);

    // Model to use
    this.model = model || this.getDefaultModel();
  }

  private initializeProvider(
    provider: string | LLMProvider,
    model?: string,
    kwargs: any = {}
  ): void {
    if (typeof provider === 'object' && 'generate' in provider) {
      this.provider = provider as BaseLLMProvider;
      this.providerName = provider.constructor.name;
    } else {
      // String provider name - load from registry
      const providerLower = (provider as string).toLowerCase();
      if (!(providerLower in PROVIDERS)) {
        throw new Error(`Unknown provider: ${provider}. Available: ${Object.keys(PROVIDERS).join(', ')}`);
      }

      const ProviderClass = PROVIDERS[providerLower];
      const providerArgs = { ...kwargs };
      if (model) {
        providerArgs.model = model;
      }

      this.provider = new ProviderClass(providerArgs);
      this.providerName = providerLower;
    }

    // Set MCP client for LangChain provider
    if ('setMcpClient' in this.provider) {
      (this.provider as any).setMcpClient(this.mcp);
    }
  }

  private getDefaultModel(): string {
    const defaults: Record<string, string> = {
      anthropic: 'claude-3-5-sonnet-20241022',
      openai: 'gpt-4o',
      gemini: 'gemini-2.0-flash-exp'
    };
    return defaults[this.providerName] || 'default';
  }

  /**
   * Helper function to properly serialize tool results
   */
  private serializeToolResult(result: any): string {
    if (result === null || result === undefined) {
      return 'null';
    }
    
    if (typeof result === 'string') {
      return result;
    }
    
    if (typeof result === 'number' || typeof result === 'boolean') {
      return String(result);
    }
    
    // For objects and arrays, use JSON.stringify with pretty formatting
    try {
      return JSON.stringify(result, null, 2);
    } catch (error) {
      // Fallback for circular references or other JSON errors
      return `[Object: ${Object.prototype.toString.call(result)}]`;
    }
  }

  async initialize(): Promise<void> {
    // Connect to MCP server and get tools
    try {
      await this.mcp.connect();
      const tools = await this.mcp.listTools();
      this.allTools = tools;
      
      // Extract categories for debugging
      const categories = new Set<string>();
    } catch (error) {
      console.error('❌ Failed to load tools from MCP server:', error);
      console.error(`   Server: ${this.serverName} at ${this.serverUrl}`);
      console.error('   This could be due to:');
      console.error('   - MCP server is not running');
      console.error('   - Incorrect server URL or authentication');
      console.error('   - Network connectivity issues');
      console.error('   - Server does not support the MCP protocol');
      console.warn('⚠️  Falling back to mock tools for testing');
      // Fallback to mock tools for testing
      this.allTools = [
        { name: 'search_web', description: 'Search the web for information' },
        { name: 'read_file', description: 'Read contents of a file' },
        { name: 'write_file', description: 'Write contents to a file' }
      ];
    }

    // Add tools to filter if filtering is enabled
    if (this.enableFiltering && this.toolFilter) {
      this.toolFilter.addTools(this.allTools);
    }

    console.debug(`Loaded ${this.allTools.length} tools from ${this.serverName}`);
    if (this.enableFiltering && this.toolFilter) {
      console.debug(`Categories discovered: ${this.toolFilter.getCategories().join(', ')}`);
    }
  }

  async chat(
    message: string,
    maxTools: number = 20,
    minScore: number = 8.0,
    context?: Record<string, any>,
    executeTools: boolean = true
  ): Promise<ChatResponse> {
    // Add user message to history
    this.messages.push({ role: 'user', content: message });

    let filteredToolsCount: number;
    let filteredToolsList: string[];

    // When filtering is enabled, use LangChain for ALL providers
    if (this.enableFiltering && this.toolFilter) {
      const filteredTools = await this.toolFilter.filterTools(message, maxTools, minScore, context);

      console.debug(`Filtered to ${filteredTools.length} relevant tools for query: "${message}"`);
      if (filteredTools.length > 0) {
        console.debug(`Top tools: ${filteredTools.slice(0, 5).map(t => t.name).join(', ')}`);
      }

      // Use LangChain for all providers when filtering is enabled
      try {
        // Create LangChain LLM based on provider
        let llm: any;
        if (this.providerName === 'anthropic') {
          llm = new ChatAnthropic({
            model: this.model,
            temperature: 0.7,
            maxTokens: 1000,
            apiKey: process.env.ANTHROPIC_API_KEY
          });
        } else if (this.providerName === 'openai') {
          llm = new ChatOpenAI({
            model: this.model,
            temperature: 0.7,
            maxTokens: 1000,
            apiKey: process.env.OPENAI_API_KEY
          });
        } else if (this.providerName === 'gemini') {
          llm = new ChatGoogleGenerativeAI({
            model: this.model,
            temperature: 0.7,
            maxOutputTokens: 1000,
            apiKey: process.env.GOOGLE_API_KEY
          });
        } else {
          throw new Error(`Unsupported provider for LangChain: ${this.providerName}`);
        }

        // Create LangChain adapter
        const adapter = new LangChainAdapter(this.mcp);

        // Convert filtered tools to LangChain format
        const originalFilteredTools = [];
        for (const filteredTool of filteredTools) {
          const originalTool = this.allTools.find(t => t.name === filteredTool.name);
          if (originalTool) {
            originalFilteredTools.push(originalTool);
          }
        }

        const langchainTools = adapter.convertToolsToLangchain(originalFilteredTools);

        // For OpenAI, bind tools directly to the model for optimal performance
        if (this.providerName === 'openai' && langchainTools.length > 0) {
          llm = llm.bind({
            tools: langchainTools,
            tool_choice: 'auto'
          });
        }

        let response: ChatResponse;

        if (langchainTools.length > 0) {
          // Create agent prompt with more explicit tool usage instructions
          const systemMessage = `You are a helpful AI assistant with access to various tools.

IMPORTANT: You MUST use the available tools to answer questions whenever relevant tools are available. Do not try to answer from your knowledge when a tool could provide the information.

Available tools:
${langchainTools.map(t => `- ${t.name}: ${t.description.replace(/\{/g, '{{').replace(/\}/g, '}}')}`).join('\n')}

When asked about web content, YouTube videos, or anything that requires external information, you MUST use the appropriate tools.`;

          const prompt = ChatPromptTemplate.fromMessages([
            ["system", systemMessage],
            new MessagesPlaceholder("chat_history"),
            ["human", "{input}"],
            new MessagesPlaceholder("agent_scratchpad"),
          ]);

          // Create the agent - use OpenAI-specific agent for OpenAI provider
          let agent: any;
          if (this.providerName === 'openai') {
            // Use OpenAI Tools agent for better tool calling performance and stability
            agent = await createOpenAIToolsAgent({ llm, tools: langchainTools, prompt });
          } else {
            // For Gemini and other providers, bind tools to LLM first
            const llmWithTools = llm.bindTools(langchainTools);
            
            agent = await createToolCallingAgent({ llm: llmWithTools, tools: langchainTools, prompt });
          }

          const agentExecutor = new AgentExecutor({
            agent,
            tools: langchainTools,
            verbose: false,
            maxIterations: 10,
            returnIntermediateSteps: true,
            handleParsingErrors: true
          });

          // Convert messages to LangChain format for chat history
          const langchainHistory = [];
          for (let i = 0; i < this.messages.length - 1; i++) {
            const msg = this.messages[i];
            if (msg.role === 'user') {
              langchainHistory.push(new HumanMessage(msg.content));
            } else if (msg.role === 'assistant') {
              langchainHistory.push(new AIMessage(msg.content));
            }
          }

          // Run the agent
          try {
            const currentQuery = this.messages[this.messages.length - 1].content;
            const result = await agentExecutor.invoke({
              input: currentQuery,
              chat_history: langchainHistory
            });

            // Extract tool calls from intermediate steps
            const toolCalls = [];
            if (result.intermediateSteps && Array.isArray(result.intermediateSteps)) {
              for (const step of result.intermediateSteps) {
                if (Array.isArray(step) && step.length >= 2) {
                  const [action, observation] = step;
                  if (action && 'tool' in action && 'toolInput' in action) {
                    toolCalls.push({
                      name: action.tool,
                      input: typeof action.toolInput === 'object' ? action.toolInput : { input: action.toolInput }
                    });
                  }
                }
              }
            }

            // Handle Gemini's specific response format
            if (toolCalls.length === 0 && Array.isArray(result.output)) {
              for (const outputItem of result.output) {
                if (outputItem && typeof outputItem === 'object' && 'functionCall' in outputItem) {
                  const funcCall = outputItem.functionCall;
                  if (funcCall && funcCall.name) {
                    toolCalls.push({
                      name: funcCall.name,
                      input: funcCall.args || {}
                    });
                  }
                }
              }
            }

            // Extract content properly for different providers
            let content = '';
            if (typeof result.output === 'string') {
              content = result.output;
            } else if (Array.isArray(result.output)) {
              // For Gemini, extract text content from array
              for (const item of result.output) {
                if (typeof item === 'string') {
                  content += item;
                } else if (item && typeof item === 'object' && 'text' in item) {
                  content += item.text;
                }
              }
            } else {
              content = String(result.output || '');
            }

            response = {
              content: content,
              toolCalls: toolCalls,
              filteredToolsCount: filteredTools.length,
              filteredTools: filteredTools.map(t => t.name),
              usedFiltering: true
            };
          } catch (error) {
            console.error('Agent execution error:', error);
            response = {
              content: 'I encountered an error while trying to use the tools. Please try again.',
              toolCalls: [],
              filteredToolsCount: filteredTools.length,
              filteredTools: filteredTools.map(t => t.name),
              usedFiltering: true
            };
          }
        } else {
          // No tools, just use LLM directly
          const langchainHistory = [];
          for (let i = 0; i < this.messages.length - 1; i++) {
            const msg = this.messages[i];
            if (msg.role === 'user') {
              langchainHistory.push(new HumanMessage(msg.content));
            } else if (msg.role === 'assistant') {
              langchainHistory.push(new AIMessage(msg.content));
            }
          }

          const messagesToSend = [
            new SystemMessage('You are a helpful AI assistant.'),
            ...langchainHistory,
            new HumanMessage(this.messages[this.messages.length - 1].content)
          ];

          const responseMsg = await llm.invoke(messagesToSend);
          response = {
            content: responseMsg.content,
            toolCalls: [],
            filteredToolsCount: 0,
            filteredTools: [],
            usedFiltering: true
          };
        }

        filteredToolsCount = filteredTools.length;
        filteredToolsList = filteredTools.map(t => t.name);

        // Add assistant response to history
        this.messages.push({ role: 'assistant', content: response.content });

        return response;
      } catch (error) {
        console.error('LangChain error:', error);
        throw error;
      }
    } else {
      
      let response: any;
      
      if (this.providerName === 'anthropic') {
        
        // Anthropic with native MCP support
        const mcpConfig = {
          type: "url",
          url: this.serverUrl,
          name: this.serverName
        };
        
        // Add authorization token if available
        if (this.authToken) {
          (mcpConfig as any).authorization_token = this.authToken;
        }
        
        response = await this.provider.generate({
          messages: this.messages,
          mcp_config: [mcpConfig],
          max_tokens: 1000,
          temperature: 0.7
        });
      } else if (this.providerName === 'gemini') {
        
        // Gemini with FastMCP session
        const mcpConfig = { session: this.mcp.session };
        
        response = await this.provider.generate({
          messages: this.messages,
          mcp_config: mcpConfig,
          tools: this.allTools,
          max_tokens: 1000,
          temperature: 0.7
        });
      } else if (this.providerName === 'openai') {
        
        // OpenAI - convert tools to provider-specific format
        const providerTools: any[] = [];
        
        for (const tool of this.allTools) {
          // OpenAI expects 'parameters' format
          providerTools.push({
            type: 'function',
            function: {
              name: tool.name,
              description: tool.description || "",
              parameters: tool.inputSchema || { type: "object", properties: {} }
            }
          });
        }

        response = await this.provider.generate({
          messages: this.messages,
          tools: providerTools.length > 0 ? providerTools : undefined,
          max_tokens: 1000,
          temperature: 0.7
        });
      } else {
        throw new Error(`Unsupported provider: ${this.providerName}`);
      }
      
      filteredToolsCount = this.allTools.length;
      filteredToolsList = this.allTools.map(t => t.name);

      // Extract response
      const content = response.content || '';
      const toolCalls = [];

      // Handle tool calls from response
      for (const tc of response.toolCalls || []) {
        if (tc.type === 'function') {
          const func = tc.function || {};
          let args = {};
          try {
            args = JSON.parse(func.arguments || '{}');
          } catch {
            // Invalid JSON
          }

          toolCalls.push({
            name: func.name,
            input: args
          });
        }
      }

      // Add assistant response to history (consistent with filtering enabled path)
      this.messages.push({ role: 'assistant', content });

      return {
        content,
        toolCalls: toolCalls,
        filteredToolsCount: filteredToolsCount,
        filteredTools: filteredToolsList,
        usedFiltering: false
      };
    }
  }

  async executeTool(toolName: string, toolInput: Record<string, any>): Promise<any> {
    try {
      const result = await this.mcp.callTool(toolName, toolInput);
      return result;
    } catch (error) {
      console.error(`Error executing tool ${toolName}:`, error);
      throw error;
    }
  }

  resetConversation(): void {
    this.messages = [];
  }

  getConversationHistory(): Message[] {
    return [...this.messages];
  }

  async chatWithTools(
    message: string,
    maxTools: number = 20,
    minScore: number = 8.0
  ): Promise<ChatWithToolsResponse> {
    // Get initial response with tool calls
    const initialResponse = await this.chat(message, maxTools, minScore);

    // If no tool calls, return the response as is
    if (!initialResponse.toolCalls || initialResponse.toolCalls.length === 0) {
      return initialResponse;
    }

    // Execute tools and collect results
    const toolResults: ToolResult[] = [];
    for (const toolCall of initialResponse.toolCalls) {
      try {
        const result = await this.executeTool(toolCall.name, toolCall.input);
        toolResults.push({
          tool: toolCall.name,
          result: this.serializeToolResult(result)
        });
      } catch (error) {
        toolResults.push({
          tool: toolCall.name,
          error: String(error)
        });
      }
    }

    // Format tool results for the assistant
    const toolResultsText = toolResults
      .map(r => `Tool: ${r.tool}\nResult: ${r.result || r.error || 'No result'}`)
      .join('\n\n');

    // Add tool results to conversation
    this.messages.push({
      role: 'user',
      content: `Here are the results from the tools:\n\n${toolResultsText}\n\nPlease provide a final response based on these results.`
    });

    // Get final response from the provider
    const finalResponse = await this.provider.generate({
      messages: this.messages,
      max_tokens: 1000
    });

    // Extract final content
    const finalContent = finalResponse.content || '';

    // Add to history
    this.messages.push({ role: 'assistant', content: finalContent });

    return {
      content: finalContent,
      initialResponse: initialResponse.content,
      toolCalls: initialResponse.toolCalls,
      toolResults: toolResults,
      filteredToolsCount: initialResponse.filteredToolsCount,
      filteredTools: initialResponse.filteredTools,
      usedFiltering: initialResponse.usedFiltering
    };
  }

  async* chatStream(
    message: string,
    maxTools: number = 20,
    minScore: number = 8.0
  ): AsyncGenerator<StreamChunk, void, unknown> {
    // Add user message to history
    this.messages.push({ role: 'user', content: message });

    // Get filtered tools if filtering is enabled
    let filteredTools: any[] = [];
    let providerTools: any[] = [];
    let filteredToolsCount = 0;
    let filteredToolsList: string[] = [];

    if (this.enableFiltering && this.toolFilter) {
      filteredTools = await this.toolFilter.filterTools(message, maxTools, minScore);
      
      // Convert tools to provider-specific format
      for (const tool of filteredTools) {
        const originalTool = this.allTools.find(t => t.name === tool.name);
        if (originalTool) {
          if (this.providerName === 'openai') {
            // OpenAI expects 'parameters' format
            providerTools.push({
              type: 'function',
              function: {
                name: originalTool.name,
                description: originalTool.description || "",
                parameters: originalTool.inputSchema || { type: "object", properties: {} }
              }
            });
          } else {
            // Anthropic and other providers expect 'input_schema' format
            providerTools.push({
              name: originalTool.name,
              description: originalTool.description || "",
              input_schema: originalTool.inputSchema || { type: "object", properties: {} }
            });
          }
        }
      }
      
      filteredToolsCount = filteredTools.length;
      filteredToolsList = filteredTools.map(t => t.name);
    } else {
      // Use all tools when filtering is disabled
      // Unified tool conversion logic for all providers
      for (const tool of this.allTools) {
        if (this.providerName === 'openai') {
          // OpenAI expects 'parameters' format
          providerTools.push({
            type: 'function',
            function: {
              name: tool.name,
              description: tool.description || "",
              parameters: tool.inputSchema || { type: "object", properties: {} }
            }
          });
        } else if (this.providerName === 'anthropic') {
          // Anthropic expects 'input_schema' format
          providerTools.push({
            name: tool.name,
            description: tool.description || "",
            input_schema: tool.inputSchema || { type: "object", properties: {} }
          });
        } else if (this.providerName === 'gemini') {
          // Gemini expects tools in their original format (pass through)
          providerTools.push(tool);
        } else {
          // Default: pass through as-is
          providerTools.push(tool);
        }
      }

      filteredToolsCount = this.allTools.length;
      filteredToolsList = this.allTools.map(t => t.name);
    }

    // Stream response from provider
    let accumulatedContent = "";
    const toolCalls: any[] = [];

    // IMPORTANT: When filtering is enabled, we should use LangChain for consistency
    // with the regular chat() method. However, since LangChain agents don't have 
    // direct streaming that matches our interface, we'll fallback to non-streaming
    // for the initial response when filtering is enabled, then stream the content.
    
    if (this.enableFiltering && this.toolFilter) {
      
      // Use the regular chat method to get the initial response with proper filtering
      const chatResponse = await this.chat(message, maxTools, minScore);
      
      // Simulate streaming the content
      if (chatResponse.content) {
        
        // Extract text content based on provider format
        let textContent = '';
        
        if (Array.isArray(chatResponse.content)) {
          // Anthropic format: array of content blocks
          for (const contentBlock of chatResponse.content) {
            if (contentBlock.type === 'text' && contentBlock.text) {
              textContent += contentBlock.text;
            }
          }
        } else if (typeof chatResponse.content === 'string') {
          // Simple string format
          textContent = chatResponse.content;
        } else {
          // Other formats - try to extract text
          textContent = String(chatResponse.content);
        }
        
        if (textContent) {
          const words = textContent.split(' ');
          for (let i = 0; i < words.length; i++) {
            const chunk = i === words.length - 1 ? words[i] : words[i] + ' ';
            accumulatedContent += chunk;
            yield {
              type: "content",
              content: chunk
            };
            // Small delay to simulate streaming
            await new Promise(resolve => setTimeout(resolve, 30));
          }
        }
      }

      // Yield any tool calls
      if (chatResponse.toolCalls) {
        for (const toolCall of chatResponse.toolCalls) {
          toolCalls.push(toolCall);
          yield {
            type: "tool_call",
            toolCall: toolCall
          };
        }
      }

      // Add assistant response to history (if not already added by chat())
      if (this.messages[this.messages.length - 1]?.role !== 'assistant') {
        this.messages.push({ role: "assistant", content: accumulatedContent });
      }
      
      // Yield final metadata
      yield {
        type: "metadata",
        filteredToolsCount: chatResponse.filteredToolsCount || 0,
        filteredTools: chatResponse.filteredTools || [],
        usedFiltering: true,
        toolCalls: toolCalls
      };
      return;
    }

    // Streaming for non-filtering (native MCP) mode
    // Prepare tools and MCP config for each provider
    let toolsToUse: any[] | undefined = undefined;
    let mcpConfig: any = undefined;

    if (this.providerName === 'openai' && this.allTools && this.allTools.length > 0) {
      toolsToUse = this.allTools.map(tool => ({
        type: 'function',
        function: {
          name: tool.name,
          description: tool.description || "",
          parameters: tool.inputSchema || { type: "object", properties: {} }
        }
      }));
    } else if (this.providerName === 'gemini' && this.allTools && this.allTools.length > 0) {
      toolsToUse = this.allTools;
      // Gemini with FastMCP session
      mcpConfig = { session: this.mcp.session };
    } else if (this.providerName === 'anthropic') {
      // Anthropic with native MCP support
      mcpConfig = {
        type: "url",
        url: this.serverUrl,
        name: this.serverName
      };
      if (this.authToken) {
        (mcpConfig as any).authorization_token = this.authToken;
      }
    }

    try {
      if (!this.provider.generateStream) {
        throw new Error(`Provider ${this.providerName} does not support streaming`);
      }

      // Build the streaming request
      const streamRequest: any = {
        messages: this.messages,
        max_tokens: 1000,
        temperature: 0.7
      };
      if (toolsToUse) {
        streamRequest.tools = toolsToUse;
      }
      if (this.providerName === 'gemini' && mcpConfig) {
        streamRequest.mcp_config = mcpConfig;
      }
      if (this.providerName === 'anthropic' && mcpConfig) {
        streamRequest.mcp_config = [mcpConfig];
      }

      for await (const chunk of this.provider.generateStream(streamRequest)) {
        if (chunk.type === "content") {
          accumulatedContent += chunk.content || "";
          yield {
            type: "content",
            content: chunk.content
          };
        } else if (chunk.type === "tool_call") {
          toolCalls.push(chunk.toolCall);
          yield {
            type: "tool_call",
            toolCall: chunk.toolCall
          };
        } else if (chunk.type === "done") {
          // Add assistant response to history
          this.messages.push({ role: "assistant", content: accumulatedContent });

          // Yield final metadata
          yield {
            type: "metadata",
            filteredToolsCount: this.allTools ? this.allTools.length : 0,
            filteredTools: this.allTools ? this.allTools.map(t => t.name) : [],
            usedFiltering: false,
            toolCalls: toolCalls
          };
          break;
        }
      }
    } catch (error) {
      console.error('Error in chatStream:', error);
      throw error;
    }
  }

  async* chatWithToolsStream(
    message: string,
    maxTools: number = 20,
    minScore: number = 8.0
  ): AsyncGenerator<StreamChunk, void, unknown> {
    // Phase 1: Initial response
    yield { type: "phase", phase: "initial_response" };

    const initialToolCalls: any[] = [];
    let accumulatedContent = "";
    let metadata: any;

    for await (const chunk of this.chatStream(message, maxTools, minScore)) {
      if (chunk.type === "content") {
        accumulatedContent += chunk.content || "";
        yield chunk;
      } else if (chunk.type === "tool_call") {
        initialToolCalls.push(chunk.toolCall);
        yield chunk;
      } else if (chunk.type === "metadata") {
        metadata = chunk;
        break;
      }
    }

    // If no tool calls, we're done
    if (!initialToolCalls || initialToolCalls.length === 0) {
      yield {
        type: "done",
        final_response: {
          content: accumulatedContent,
          toolCalls: [],
          toolResults: [],
          filteredToolsCount: metadata.filteredToolsCount || 0,
          filteredTools: metadata.filteredTools || [],
          usedFiltering: metadata.usedFiltering || false
        }
      };
      return;
    }

    // Phase 2: Tool execution
    yield { type: "phase", phase: "tool_execution" };

    const toolResults: ToolResult[] = [];
    for (const toolCall of initialToolCalls) {
      try {
        // Parse tool call arguments
        const toolName = toolCall.name || "";
        
        // Skip empty tool names
        if (!toolName) {
          continue;
        }

        // Parse arguments
        let args = toolCall.input || {};
        
        const result = await this.executeTool(toolName, args);
        toolResults.push({
          tool: toolName,
          result: this.serializeToolResult(result)
        });

        yield {
          type: "tool_result",
          toolName: toolName,
          result: this.serializeToolResult(result)
        };
      } catch (error) {
        const toolName = toolCall.name || "";
        toolResults.push({
          tool: toolName,
          error: String(error)
        });

        yield {
          type: "tool_error",
          toolName: toolName,
          error: String(error)
        };
      }
    }

    // Phase 3: Final response
    yield { type: "phase", phase: "final_response" };

    // Format tool results for the assistant
    const toolResultsText = toolResults
      .map(r => `Tool: ${r.tool}\nResult: ${r.result || r.error || 'No result'}`)
      .join('\n\n');

    // Add tool results to conversation
    this.messages.push({
      role: "user",
      content: `Here are the results from the tools:\n\n${toolResultsText}\n\nPlease provide a final response based on these results.`
    });

    // Stream final response
    let finalContent = "";

    // For final response, we don't need tools or MCP config - just generate response from conversation history
    // This is consistent regardless of filtering status

    try {
      if (!this.provider.generateStream) {
        throw new Error(`Provider ${this.providerName} does not support streaming`);
      }

      for await (const chunk of this.provider.generateStream({
        messages: this.messages,
        max_tokens: 1000
      })) {
        if (chunk.type === "content") {
          finalContent += chunk.content || "";
          yield {
            type: "final_content",
            content: chunk.content
          };
        } else if (chunk.type === "done") {
          // Add to history
          this.messages.push({ role: "assistant", content: finalContent });
          
          // Yield completion
          yield {
            type: "done",
            final_response: {
              content: finalContent,
              initialResponse: accumulatedContent,
              toolCalls: initialToolCalls,
              toolResults: toolResults,
              filteredToolsCount: metadata.filteredToolsCount || 0,
              filteredTools: metadata.filteredTools || [],
              usedFiltering: metadata.usedFiltering || false
            }
          };
          break;
        }
      }
    } catch (error) {
      console.error('Error in final response streaming:', error);
      throw error;
    }
  }

  async chatWithToolsStreaming(
    message: string,
    maxTools: number = 20,
    minScore: number = 8.0
  ): Promise<ChatWithToolsResponse> {
    // Get initial response with tool calls
    const initialResponse = await this.chat(message, maxTools, minScore);

    // If no tool calls, return the response as is
    if (!initialResponse.toolCalls || initialResponse.toolCalls.length === 0) {
      return initialResponse;
    }

    // Execute tools and collect results
    const toolResults: ToolResult[] = [];
    for (const toolCall of initialResponse.toolCalls) {
      try {
        const result = await this.executeTool(toolCall.name, toolCall.input);
        toolResults.push({
          tool: toolCall.name,
          result: this.serializeToolResult(result)
        });
      } catch (error) {
        toolResults.push({
          tool: toolCall.name,
          error: String(error)
        });
      }
    }

    // Format tool results for the assistant
    const toolResultsText = toolResults
      .map(r => `Tool: ${r.tool}\nResult: ${r.result || r.error || 'No result'}`)
      .join('\n\n');

    // Add tool results to conversation
    this.messages.push({
      role: 'user',
      content: `Here are the results from the tools:\n\n${toolResultsText}\n\nPlease provide a final response based on these results.`
    });

    // Get final response from the provider
    const finalResponse = await this.provider.generate({
      messages: this.messages,
      max_tokens: 1000
    });

    // Extract final content
    const finalContent = finalResponse.content || '';

    // Add to history
    this.messages.push({ role: 'assistant', content: finalContent });

    return {
      content: finalContent,
      initialResponse: initialResponse.content,
      toolCalls: initialResponse.toolCalls,
      toolResults: toolResults,
      filteredToolsCount: initialResponse.filteredToolsCount,
      filteredTools: initialResponse.filteredTools,
      usedFiltering: initialResponse.usedFiltering
    };
  }

  async close(): Promise<void> {
    await this.mcp.close();
  }
}