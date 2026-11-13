declare module '@jeejio-bubble/bot/sdk/WebApp.js' {
  export class BubbleWebApp {
    constructor(options?: Record<string, unknown>);
    ble: unknown;
    getDevice?(options?: Record<string, unknown>): Promise<unknown>;
    getDevices(options?: Record<string, unknown>): Promise<unknown>;
    subscribeDeviceEvents(device: unknown): Promise<unknown>;
    onDeviceEvent(handler: (event: unknown) => void): void;
    callDevice(device: unknown, rpc: unknown): Promise<unknown>;
  }
}


declare module '@jeejio-bubble/bot/sdk/BleAppSession.js' {
  export class BleAppSession {
    constructor(ble: unknown, options?: Record<string, unknown>);
    send(device: unknown, payload: Record<string, unknown>, options?: Record<string, unknown>): Promise<unknown>;
    handshake(device: unknown, options?: Record<string, unknown>): Promise<unknown>;
    setConfig(name: string, value: unknown, options?: Record<string, unknown>): Promise<unknown>;
    on(type: string, handler: (event: { message?: unknown; text?: string; raw?: unknown }) => void): void;
    off(type: string, handler: (event: { message?: unknown; text?: string; raw?: unknown }) => void): void;
  }
}
declare module '@jeejio-bubble/bot/sdk/BleAppClient.js' {
  export class BleAppClient {
    constructor(ble: unknown, options?: Record<string, unknown>);
    state: { connection: string; message: string; lastError: string };
    ensureConnected(device?: unknown, options?: Record<string, unknown>): Promise<unknown>;
    reconnect(options?: Record<string, unknown>): Promise<unknown>;
    send(device: unknown, payload: Record<string, unknown>, options?: Record<string, unknown>): Promise<unknown>;
    setConfig(name: string, value: unknown, options?: Record<string, unknown>): Promise<unknown>;
    on(type: string, handler: (event: any) => void): this;
    off(type: string, handler: (event: any) => void): this;
  }
  export function isBleAppDisconnectError(error: unknown): boolean;
}
