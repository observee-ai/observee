import axios from 'axios';
import fs from 'fs';
import { LoggerConfig, OBSERVEE_API_ENDPOINT, PromptUsageData, ToolUsageData } from './types.js';
import { createLogFilePath, ensureDirectoryExists } from './utils.js';

export class Logger {
    private apiKey: string | null;
    private logFilePath: string | null;
    private mcpServerName: string;

    constructor(mcpServerName: string, config?: LoggerConfig) {
        this.mcpServerName = mcpServerName;
        this.apiKey = config?.apiKey ?? null;
        
        // If logFile is specified, create the log file in system logs directory
        if (config?.logFile) {
            this.logFilePath = createLogFilePath(config.logFile);
        } else {
            this.logFilePath = null;
        }

        // Ensure the log directory exists if we're using file logging
        if (this.logFilePath) {
            ensureDirectoryExists(this.logFilePath);
        }
    }

    async log(data: Omit<ToolUsageData, 'mcp_server_name'> | Omit<PromptUsageData, 'mcp_server_name'>): Promise<void> {
        const enhancedData = {
            ...data,
            mcp_server_name: this.mcpServerName,
            timestamp: new Date().toISOString()
        };

        // Prioritize API logging if API key is available
        if (this.apiKey) {
            try {
                await axios.post(OBSERVEE_API_ENDPOINT, enhancedData, {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': `${this.apiKey}`
                    },
                    timeout: 30000 // 30 second timeout
                });
                return; // Successfully logged to API, no need for file logging
            } catch (error) {
                console.error(`Failed to send log request: ${error instanceof Error ? error.message : String(error)}`);
                // Fall through to file logging as backup if available
            }
        }

        // Use file logging if available (either as primary or backup)
        if (this.logFilePath) {
            try {
                fs.appendFileSync(this.logFilePath, JSON.stringify(enhancedData) + "\n");
            } catch (error) {
                console.error(`Failed to write to log file: ${error instanceof Error ? error.message : String(error)}`);
            }
        } else if (!this.apiKey) {
            throw new Error("No API key or log file configured for logging");
        }
    }

    /**
     * Gets the current log file path (if file logging is enabled)
     */
    getLogFilePath(): string | null {
        return this.logFilePath;
    }

    /**
     * Gets the MCP server name
     */
    getServerName(): string {
        return this.mcpServerName;
    }
} 