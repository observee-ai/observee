/**
 * BM25-based tool filtering - simple keyword matching implementation
 * This is a simplified version without external dependencies for now
 */

import crypto from 'crypto';
import { createRequire } from 'module';
import type { BMDocument } from "okapibm25";
import { Tool } from '../types.js';
import { BaseToolFilter } from './base.js';

// Use createRequire to import CommonJS module
const require = createRequire(import.meta.url);
const BM25Module = require('okapibm25');
const BM25 = BM25Module.default || BM25Module;


const COMMON_WORDS = new Set([
  'the', 'and', 'for', 'with', 'from', 'this', 'that', 'will', 'can', 
  'are', 'was', 'were', 'been', 'have', 'has', 'had', 'does', 'did',
  'not', 'but', 'what', 'when', 'where', 'which', 'who', 'how', 'why',
  'all', 'would', 'there', 'their', 'your', 'more', 'other', 'some',
  'into', 'only', 'also', 'than', 'many', 'must', 'should', 'could'
]);

export class BM25Filter extends BaseToolFilter {
  private bm25: BMDocument[];
  private corpusTokens: string[][] = [];
  private categories: Map<string, Set<Tool>> = new Map();
  private toolIndices: Map<string, number> = new Map();
  private useCache: boolean;
  private _bm25Cache: any | null = null;
  constructor(useCache: boolean = true, syncTools: boolean = false) {
    super();
    this.useCache = useCache;
    this.bm25 = [];

    console.debug(`BM25Filter constructor: useCache=${useCache}, syncTools=${syncTools}`);

    // Clear cache if syncTools is true
    if (syncTools && this._bm25Cache) {
      this.clearCache();
    }
  }

  private async clearCache(): Promise<void> {
    try {
      this._bm25Cache = null;
      console.debug('Cleared BM25 cache due to sync_tools=True');
    } catch (error) {
      console.debug(`Failed to clear cache: ${error}`);
    }
  }

  private extractMetadata(tool: Tool): Record<string, any> {
    // Ensure keywords and categories are initialized as Sets
    if (!tool.keywords) tool.keywords = new Set<string>();
    if (!tool.categories) tool.categories = new Set<string>();

    // Extract from tool name
    const nameParts = tool.name.toLowerCase().split(/[_\W]+/);
    for (const part of nameParts) {
      if (part) tool.keywords.add(part);
    }

    // Extract service/category from prefix
    if (tool.name.includes("__")) {
      const service = tool.name.split("__")[0].toLowerCase();
      tool.categories.add(service);
    }

    // Extract keywords from description
    if (tool.description) {
      const descWords = (tool.description.toLowerCase().match(/\b[a-z]+\b/g)) || [];
      const meaningfulWords = descWords.filter(
        w => w.length > 3 && !COMMON_WORDS.has(w)
      );
      for (const w of meaningfulWords.slice(0, 10)) {
        tool.keywords.add(w);
      }
    }

    // Extract from parameter names
    if (tool.parameters && typeof tool.parameters === "object" && !Array.isArray(tool.parameters)) {
      this.extractParamKeywords(tool, tool.parameters);
    }

    // Return categories and keywords for reference
    return {
      categories: tool.categories,
      keywords: tool.keywords
    };
  }

  private extractParamKeywords(tool: Tool, schema: Record<string, any>): void {
    if ("properties" in schema) {
      const properties = schema.properties || {};
      for (const [propName, propSchema] of Object.entries(properties)) {
        if (
          typeof propSchema !== "object" ||
          propSchema === null ||
          !("description" in propSchema) ||
          typeof (propSchema as any).description !== "string"
        ) {
          continue;
        }
        if (tool.keywords && typeof tool.keywords.add === "function") {
          tool.keywords.add(propName.toLowerCase());
          if (
            typeof propSchema === "object" &&
            propSchema !== null &&
            typeof propSchema.description === "string"
          ) {
            const descWords = (propSchema.description.toLowerCase().match(/\b[a-z]+\b/g)) || [];
            for (const w of descWords) {
              if (w.length > 3 && !COMMON_WORDS.has(w)) {
                tool.keywords.add(w);
              }
            }
          }
        }
        if (typeof propSchema === "object" && propSchema !== null) {
          this.extractParamKeywords(tool, propSchema);
        }
      }
    }
  }

  /**
   * Tokenize text for BM25
   */
  private tokenize(text: string): string[] {
    // Simple tokenization - lowercase and split
    const tokens = (text.toLowerCase().match(/\b[a-z]+\b/g)) || [];
    // Remove common words and short tokens
    return tokens.filter(t => !COMMON_WORDS.has(t) && t.length > 2);
  }

  /**
   * Create a searchable document string from a Tool object.
   * Combines name, description, categories, and keywords with weights.
   */
  private createToolDocument(tool: Tool): string {
    // Name is most important, also add a split version
    const name = tool.name || "";
    const splitName = name.replace(/_/g, ' ').replace(/__+/g, ' ');
    const description = tool.description || "";
    // Categories: boost by repeating
    let categories = "";
    if (Array.isArray((tool as any).categories)) {
      categories = ((tool as any).categories as string[]).join(' ');
    } else if (typeof (tool as any).category === "string") {
      categories = (tool as any).category;
    }
    const boostedCategories = (categories + " ").repeat(2).trim();
    // Keywords: limit to 20
    let keywords = "";
    if (Array.isArray((tool as any).keywords)) {
      keywords = ((tool as any).keywords as string[]).slice(0, 20).join(' ');
    }
    const parts = [
      name,
      splitName,
      description,
      boostedCategories,
      keywords
    ];
    return parts.filter(Boolean).join(' ');
  }

  /**
   * Compute a hash of the current tools for cache validation.
   */
  private computeToolsHash(): string {
    const toolData = this.tools.map((t: Tool) => [t.name, t.description]);
    const str = JSON.stringify(toolData);
    // Use Node.js crypto to compute md5 hash
    return crypto.createHash('md5').update(str).digest('hex');
  }

  /**
   * Save BM25 index and related data to cache
   */
  private async saveCache(): Promise<void> {
    if (!this.useCache) {
      return;
    }
  
    try {
      const cache_data = {
          'toolHash': this.computeToolsHash(),
          'corpusTokens': this.corpusTokens,
          'toolIndices': this.toolIndices,
          'tools': this.tools,
          'categories': Object.fromEntries(this.categories)
      }
      this._bm25Cache = JSON.stringify(cache_data);
      console.debug("Saved BM25 cache");
    } catch (error) {
      console.debug(`Failed to save cache: ${error}`);
    }
  }

  /**
   * Add tools to the BM25 index
   */
  public async addTools(tools: Tool[]): Promise<void> {
    // Process tools first to enable cache checking
    for (const toolData of tools) {
      let tool: Tool;
      if ('name' in toolData) { // Tool object
        tool = {
          name: toolData.name,
          description: toolData.description || "",
          server: this.extractServerFromName ? this.extractServerFromName(toolData.name) : "",
          parameters: 'inputSchema' in toolData ? toolData.inputSchema as Record<string, any> : {}
        };
      } else { // Dict format
        tool = {
          name: toolData["name"] || "",
          description: toolData["description"] || "",
          server: toolData["server"] || (this.extractServerFromName ? this.extractServerFromName(toolData["name"] || "") : ""),
          parameters: toolData["inputSchema"] as Record<string, any> || {}
        };
      }
      // extract Metadata
      this.extractMetadata(tool);
      this.tools.push(tool);
    }

    // if (this.useCache) {
    //   console.debug(`BM25Filter addTools: useCache=true, skipping corpus creation`);
    //   return;
    // }

    let corpus = []

    for (let i = 0; i < this.tools.length; i++) {
      const tool = this.tools[i];
      const categories = tool.categories ? Array.from(tool.categories) : [];
      for (const category of categories) {
        if (!this.categories.has(category)) {
          this.categories.set(category, new Set());
        }
        this.categories.get(category)!.add(tool);
      }
      const document = this.createToolDocument(tool); 
      const tokens = this.tokenize(document);
      corpus.push(tokens);
      this.toolIndices.set(tool.name, i);
    }

    this.corpusTokens = corpus;

    const nonEmptyDocuments = corpus.filter(doc => doc.length > 0);
    if (nonEmptyDocuments.length === 0) {
      corpus = [["dummy"]];
    }


    this.bm25 = BM25(corpus.flat(), [], { b: 1.5, k1: 0.75 }) as BMDocument[];


    this.saveCache();
  }


  /**
   * Filter tools using BM25
   */
  public async filterTools(query: string, maxTools: number = 10, minScore: number = 5.0, context: Record<string, any> = {}): Promise<Tool[]> {  
    const queryTokens = this.tokenize(query);
    if (!queryTokens.length) {
      return [];
    }
    console.debug(`Query tokens: ${queryTokens}`);

    // and returns (results, scores) tuple
    // Get all scores for the query using BM25
    const bmDocuments = Array.isArray(this.bm25)
      ? [...this.bm25].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
      : this.bm25;

    const queryLower = query.toLowerCase();
    const scoredTools: [number, Tool][] = [];

    // Assume bmDocuments is an array of BMDocument with .score and .document (the tool doc string)
    // We need to map bmDocuments to tool indices
    // We'll use the index in bmDocuments as the tool index
    for (let idx = 0; idx < bmDocuments.length; idx++) {
      const bmDoc = bmDocuments[idx];
      if (idx >= this.tools.length) continue;
      const tool = this.tools[idx];

      // Start with BM25 score (scale it up)
      let totalScore = (typeof bmDoc.score === "number" ? bmDoc.score : 0) * 10;

      // Add boosts for exact matches
      if (queryLower && tool.name && tool.name.toLowerCase().includes(queryLower)) {
        totalScore += 50.0;
      } else if (queryTokens.some(token => tool.name && tool.name.toLowerCase().includes(token))) {
        totalScore += 20.0;
      }

      // Category match boost
      if (tool.categories) {
        for (const category of tool.categories) {
          if (queryLower.includes(category.toLowerCase())) {
            totalScore += 30.0;
            break;
          }
        }
      }

      // Context boosts
      if (context) {
        if (context.previous_tools && Array.isArray(context.previous_tools)) {
          for (const prevTool of context.previous_tools) {
            if (await this.areToolsRelated(query, prevTool, tool.name)) {
              totalScore += 10.0;
            }
          }
        }
        if (context.tool_hints && Array.isArray(context.tool_hints)) {
          for (const hint of context.tool_hints) {
            const hintLower = hint.toLowerCase();
            if (tool.name && tool.name.toLowerCase().includes(hintLower)) {
              totalScore += 20.0;
            } else if (
              tool.categories &&
              Array.from(tool.categories).some(cat => cat.toLowerCase().includes(hintLower))
            ) {
              totalScore += 15.0;
            }
          }
        }
      }

      if (totalScore > 0) {
        scoredTools.push([totalScore, tool]);
      }
    }

    // Sort by total score
    scoredTools.sort((a, b) => b[0] - a[0]);

    // Apply threshold
    let filtered = scoredTools.filter(([score, _tool]) => score >= minScore);

    // Ensure at least 3 results if available
    if (filtered.length < 3 && scoredTools.length >= 3) {
      filtered = scoredTools.slice(0, 3);
    }

    // Apply diversity and limit
    let tools: Tool[];
    if (filtered.length > maxTools) {
      tools = await this.applyDiversity(filtered, maxTools);
    } else {
      tools = filtered.slice(0, maxTools).map(([_, tool]) => tool);
    }

    return tools;
  }

  /**
   * Check if tools are related to a query
   */
  protected async areToolsRelated(query: string, firstToolName: string, secondToolName: string): Promise<boolean> {
    const service1 = firstToolName.includes('__') ? firstToolName.split('__')[0] : null;
    const service2 = secondToolName.includes('__') ? secondToolName.split('__')[0] : null;
    return service1 !== null && service2 !== null && service1 === service2;
  }


  protected async applyDiversity(scoredTools: [number, Tool][], maxResults: number = 10): Promise<Tool[]> {
    const selectedTools: Tool[] = [];
    const categoryCounts = new Map<string, number>();
    const maxPerCategory = Math.max(2, Math.floor(maxResults / 3));

    for (const [score, tool] of scoredTools) {
      const toolCategories = tool.categories ? Array.from(tool.categories) : ["default"];
      const canAdd = toolCategories.every(cat => (categoryCounts.get(cat) || 0) < maxPerCategory);

      if (canAdd) {
        selectedTools.push(tool);
        for (const category of toolCategories) {
          categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
        }
      }

      if (selectedTools.length >= maxResults) {
        break;
      }
    }

    return selectedTools;
  }

  public getCategories(): string[] {
    return Array.from(this.categories.keys());
  }

  public getToolsByCategory(category: string): Tool[] {
    return Array.from(this.categories.get(category.toLowerCase()) || []);
  }
}



