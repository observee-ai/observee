/**
 * Base filter class for tool filtering strategies
 */

import { Tool } from '../types.js';

export abstract class BaseToolFilter {
  protected tools: Tool[] = [];
  protected serverName?: string;
  protected serverUrl?: string;
  protected vectorStoreManager?: any;

  constructor(vectorStoreManager?: any) {
    this.vectorStoreManager = vectorStoreManager;
  }

  setServerInfo(serverName: string, serverUrl: string): void {
    this.serverName = serverName;
    this.serverUrl = serverUrl;
  }

  abstract addTools(tools: any[]): void;

  abstract filterTools(
    query: string,
    maxTools?: number,
    minScore?: number,
    context?: Record<string, any>
  ): Promise<Tool[]>;

  getCategories(): string[] {
    return [];
  }

  getToolsByCategory(category: string): Tool[] {
    return [];
  }

  getAllTools(): Tool[] {
    return [...this.tools];
  }

  protected extractServerFromName(toolName: string): string {
    if (toolName.includes('__')) {
      return toolName.split('__')[0];
    }
    return 'default';
  }
}