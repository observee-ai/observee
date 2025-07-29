/**
 * Provider registry and exports
 */

import { BaseLLMProvider } from './base.js';
import { AnthropicProvider } from './anthropic.js';
import { OpenAIProvider } from './openai.js';
import { GeminiProvider } from './gemini.js';

export const PROVIDERS: Record<string, new (options: any) => BaseLLMProvider> = {
  anthropic: AnthropicProvider as any,
  openai: OpenAIProvider as any,
  gemini: GeminiProvider as any
};

export {
  BaseLLMProvider,
  AnthropicProvider,
  OpenAIProvider,
  GeminiProvider
};