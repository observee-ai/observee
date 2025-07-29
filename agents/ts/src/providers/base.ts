/**
 * Base LLM provider interface
 */

import { LLMResponse, Message, StreamChunk } from '../types.js';

export interface LLMProviderOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  [key: string]: any;
}

export abstract class BaseLLMProvider {
  protected model?: string;
  protected temperature: number = 0.7;
  protected maxTokens: number = 1000;

  constructor(options: LLMProviderOptions = {}) {
    if (options.model) this.model = options.model;
    if (options.temperature !== undefined) this.temperature = options.temperature;
    if (options.maxTokens !== undefined) this.maxTokens = options.maxTokens;
  }

  abstract generate(params: {
    messages: Message[];
    tools?: any[];
    mcp_config?: any;
    max_tokens?: number;
    temperature?: number;
  }): Promise<LLMResponse>;

  // Make generateStream optional for backward compatibility
  generateStream?(params: {
    messages: Message[];
    tools?: any[];
    mcp_config?: any;
    max_tokens?: number;
    temperature?: number;
  }): AsyncGenerator<StreamChunk, void, unknown>;

  setMcpClient?(mcpClient: any): void;
}