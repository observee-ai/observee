import { Logger } from './logger.js';
import { PromptUsageData, Request, Result, ToolUsageData } from './types.js';

export function observeeUsageLogger<F extends (...args: any[]) => any>(logger: Logger, handler: F) {
    const originalMethod = handler;
    return async (...args: Parameters<F>) => {
        const startTime = Date.now();
        try {
            let serverSessionId: string | null = null;
            const mainArgs = JSON.parse(JSON.stringify(args));
            const mainRequest = mainArgs[0] as Request;
            
            if (!mainRequest) {
                throw new Error("No request found");
            }

            // Extract server_session_id from arguments
            if (mainRequest.params && mainRequest.params.arguments) {
                if ('server_session_id' in mainRequest.params.arguments) {
                    const { server_session_id, ...rest } = mainRequest.params.arguments;
                    serverSessionId = server_session_id as string;
                    mainRequest.params.arguments = rest;
                    mainArgs[0] = mainRequest;
                }
            }

            const result = await originalMethod(...mainArgs) as Result;

            // Remove internal MCP parameters from logged arguments
            if (mainRequest.params.arguments) {
                if ('mcp_client_id' in mainRequest.params.arguments) {
                    const { mcp_client_id, ...rest } = mainRequest.params.arguments;
                    mainRequest.params.arguments = rest;
                    mainArgs[0] = mainRequest;
                }
                if ('mcp_customer_id' in mainRequest.params.arguments) {
                    const { mcp_customer_id, ...rest } = mainRequest.params.arguments;
                    mainRequest.params.arguments = rest;
                    mainArgs[0] = mainRequest;
                }
            }

            const request = args[0] as Request;
            
            if (request.method === "tools/call") {
                await logToolCall(logger, request, mainArgs, result, startTime, serverSessionId);
            } else if (request.method === "prompts/get") {
                await logPromptCall(logger, request, mainArgs, result, serverSessionId);
            }

            return result;
        } catch (error) {
            await logError(logger, args, error, startTime);
            throw error;
        }
    };
}

async function logToolCall(
    logger: Logger,
    request: Request,
    mainArgs: any[],
    result: Result,
    startTime: number,
    serverSessionId: string | null
): Promise<void> {
    const endTime = Date.now();
    const duration = endTime - startTime;

    const toolResponse = JSON.stringify(Object.keys(result).reduce((acc, key) => {
        acc[key] = typeof result[key] === 'object' ? JSON.stringify(result[key]) : String(result[key]);
        return acc;
    }, {} as Record<string, string>));

    const data: Omit<ToolUsageData, 'mcp_server_name'> = {
        tool_name: request.params.name || "unknown",
        tool_input: JSON.stringify(mainArgs),
        tool_response: toolResponse,
        duration: duration,
        session_id: serverSessionId ?? undefined,
    };

    await logger.log(data);
}

async function logPromptCall(
    logger: Logger,
    request: Request,
    mainArgs: any[],
    result: Result,
    serverSessionId: string | null
): Promise<void> {
    const promptResponse = JSON.stringify(Object.keys(result).reduce((acc, key) => {
        acc[key] = typeof result[key] === 'object' ? JSON.stringify(result[key]) : String(result[key]);
        return acc;
    }, {} as Record<string, string>));

    const data: Omit<PromptUsageData, 'mcp_server_name'> = {
        prompt_name: request.params.name || "unknown",
        prompt_input: JSON.stringify(mainArgs),
        prompt_response: promptResponse,
        session_id: serverSessionId ?? undefined,
    };

    await logger.log(data);
}

async function logError(
    logger: Logger,
    args: any[],
    error: unknown,
    startTime: number
): Promise<void> {
    const endTime = Date.now();
    const duration = endTime - startTime;

    const data: Omit<ToolUsageData, 'mcp_server_name'> = {
        tool_name: args[0]?.["params"]?.["name"] || "unknown",
        tool_input: JSON.stringify(args),
        tool_response: error instanceof Error ? error.message : String(error),
        duration: duration
    };

    await logger.log(data);
} 