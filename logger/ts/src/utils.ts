import fs from 'fs';
import os from 'os';
import path from 'path';

/**
 * Gets the appropriate logs directory for the current operating system
 * @returns The logs directory path
 */
export function getLogsDirectory(): string {
    const platform = os.platform();
    const homeDir = os.homedir();
    
    switch (platform) {
        case 'darwin': // macOS
            return path.join(homeDir, 'Library', 'Logs');
        case 'win32': // Windows
            return process.env.LOCALAPPDATA || path.join(homeDir, 'AppData', 'Local');
        case 'linux': // Linux
        default: // Default to Linux-style for other Unix-like systems
            return path.join(homeDir, '.cache');
    }
}

/**
 * Creates a log file path in the system logs directory
 * @param fileName The name of the log file
 * @returns The full path to the log file in the system logs directory
 */
export function createLogFilePath(fileName: string): string {
    const logsDir = getLogsDirectory();
    const observeeDir = path.join(logsDir, 'observee');
    
    return path.join(observeeDir, fileName);
}

/**
 * Ensures the directory exists for the given file path
 * @param filePath The full path to the file
 */
export function ensureDirectoryExists(filePath: string): void {
    const dir = path.dirname(filePath);
    
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
} 