# Weather Tool

## Architecture

```text
WeatherRequest
    ↓
WeatherTool
    ↓
OpenWeatherClient
    ↓
OpenWeatherMap Current Weather API
    ↓
WeatherMapper
    ↓
WeatherResult
```

The Weather Tool is isolated from the AI runtime and is not registered in `ToolRegistry` yet. It uses dependency injection and can later be wrapped or registered without changing its provider client, mapper, or immutable weather models.

## Models

- `WeatherRequest`: validated latitude and longitude.
- `WeatherResult`: immutable location, coordinates, temperature, humidity, pressure, wind, visibility, weather condition, optional one-hour rainfall, timestamp, and source.

## Configuration

Set only:

```text
OPENWEATHER_API_KEY=your-key
```

Optional non-secret settings use the `FLOOD_AWARE_WEATHER_` prefix, including `BASE_URL`, `TIMEOUT_SECONDS`, and `WEATHER_UNITS`. Units default to `metric`.

## Flow and errors

`OpenWeatherClient` makes a timed `httpx` request and converts authentication, not-found, timeout, network, invalid JSON, and HTTP failures into Weather domain exceptions. `WeatherMapper` prevents raw OpenWeatherMap JSON from crossing the package boundary.

`OpenWeatherClient` owns and closes an `httpx.Client` only when it creates that client internally. Injected clients remain externally owned and are never closed by the Weather Tool.

## Future runtime integration

Sprint 9.4 deliberately does not modify `AIRuntime`, `ToolRegistry`, or `ToolExecutor`. A later runtime composition sprint can register the injected Weather Tool while preserving its current public typed interface.
