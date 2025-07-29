import { z } from 'zod';

// Zod schema for tool usage data
export const toolUsageSchema = z.object({
    mcp_server_name: z.string(),
    tool_name: z.string(),
    tool_input: z.string().optional(),
    tool_response: z.string().optional(),
    duration: z.number(),
    session_id: z.string().optional()
});

export const promptUsageSchema = z.object({
    mcp_server_name: z.string(),
    prompt_name: z.string(),
    prompt_input: z.string().optional(),
    prompt_response: z.string().optional(),
    session_id: z.string().optional()
});

export type ToolUsageData = z.infer<typeof toolUsageSchema>;
export type PromptUsageData = z.infer<typeof promptUsageSchema>;

export interface LoggerConfig {
    apiKey?: string;
    logFile?: string;
}

export interface Request {
    method: string;
    params: {
        name: string;
        arguments?: { [key: string]: unknown };
    };
}

export interface Result {
    [key: string]: unknown;
}

export const OBSERVEE_API_ENDPOINT = "https://log.observee.ai/logs/"; 