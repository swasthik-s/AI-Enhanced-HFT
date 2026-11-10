#property strict
#property version   "0.10"
#property description "Read-only telemetry bridge for AI-Enhanced-HFT cloud control centre"

input string ApiBaseUrl = "https://your-api-host.example.com";
input string ApiKey = "";
input int HeartbeatSeconds = 5;
input int BarsToSend = 10;
input ENUM_TIMEFRAMES DataTimeframe = PERIOD_H1;

datetime last_send = 0;
int ema_fast_handle = INVALID_HANDLE;
int ema_slow_handle = INVALID_HANDLE;
int adx_handle = INVALID_HANDLE;

string JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   StringReplace(value, "\r", "");
   StringReplace(value, "\n", "\\n");
   return value;
}

string TfToString(ENUM_TIMEFRAMES tf)
{
   return EnumToString(tf);
}

string BuildPositionsJson()
{
   string out = "[";
   bool first = true;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!first) out += ",";
      first = false;
      out += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":%d,\"volume\":%.2f,\"price_open\":%.8f,\"price_current\":%.8f,\"profit\":%.2f,\"sl\":%.8f,\"tp\":%.8f}",
         ticket,
         JsonEscape(PositionGetString(POSITION_SYMBOL)),
         (int)PositionGetInteger(POSITION_TYPE),
         PositionGetDouble(POSITION_VOLUME),
         PositionGetDouble(POSITION_PRICE_OPEN),
         PositionGetDouble(POSITION_PRICE_CURRENT),
         PositionGetDouble(POSITION_PROFIT),
         PositionGetDouble(POSITION_SL),
         PositionGetDouble(POSITION_TP)
      );
   }
   return out + "]";
}

string BuildBarsJson()
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int count = CopyRates(_Symbol, DataTimeframe, 0, MathMax(1, MathMin(BarsToSend, 50)), rates);
   if(count <= 0) return "[]";
   string out = "[";
   for(int i = count - 1; i >= 0; i--)
   {
      if(i != count - 1) out += ",";
      out += StringFormat(
         "{\"time\":%I64d,\"open\":%.8f,\"high\":%.8f,\"low\":%.8f,\"close\":%.8f,\"tick_volume\":%I64d}",
         (long)rates[i].time, rates[i].open, rates[i].high, rates[i].low, rates[i].close, rates[i].tick_volume
      );
   }
   return out + "]";
}

string BuildIndicatorsJson()
{
   double fast[], slow[], adx[];
   ArraySetAsSeries(fast, true);
   ArraySetAsSeries(slow, true);
   ArraySetAsSeries(adx, true);
   if(CopyBuffer(ema_fast_handle, 0, 0, 1, fast) < 1 ||
      CopyBuffer(ema_slow_handle, 0, 0, 1, slow) < 1 ||
      CopyBuffer(adx_handle, 0, 0, 1, adx) < 1)
      return "{}";
   return StringFormat("{\"ema_fast\":%.8f,\"ema_slow\":%.8f,\"adx\":%.4f}", fast[0], slow[0], adx[0]);
}

string BuildPayload()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double spread = (point > 0) ? (ask - bid) / point : 0;
   string account = IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
   string server = JsonEscape(AccountInfoString(ACCOUNT_SERVER));
   string symbol = JsonEscape(_Symbol);

   return StringFormat(
      "{\"account_login\":\"%s\",\"server\":\"%s\",\"symbol\":\"%s\",\"timeframe\":\"%s\",\"bid\":%.8f,\"ask\":%.8f,\"spread_points\":%.2f,\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,\"free_margin\":%.2f,\"positions_count\":%d,\"positions\":%s,\"bars\":%s,\"indicators\":%s,\"ea_status\":\"running\",\"terminal_time\":\"%s\"}",
      account, server, symbol, TfToString(DataTimeframe), bid, ask, spread,
      AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY),
      AccountInfoDouble(ACCOUNT_MARGIN), AccountInfoDouble(ACCOUNT_MARGIN_FREE),
      PositionsTotal(), BuildPositionsJson(), BuildBarsJson(), BuildIndicatorsJson(),
      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)
   );
}

bool SendTelemetry()
{
   if(StringLen(ApiKey) < 20)
   {
      Print("CloudBridge: configure a strong ApiKey (minimum 20 characters).");
      return false;
   }
   string url = ApiBaseUrl + "/v1/telemetry";
   string body = BuildPayload();
   char data[];
   StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   int data_size = ArraySize(data);
   if(data_size > 0 && data[data_size - 1] == 0) ArrayResize(data, data_size - 1);

   char result[];
   string headers = "Content-Type: application/json\r\nAuthorization: Bearer " + ApiKey + "\r\n";
   string response_headers;
   ResetLastError();
   int status = WebRequest("POST", url, headers, 5000, data, result, response_headers);
   if(status == -1)
   {
      Print("CloudBridge: WebRequest failed. Error=", GetLastError(),
            ". Add the API origin to MT5 Tools > Options > Expert Advisors > Allow WebRequest.");
      return false;
   }
   if(status < 200 || status >= 300)
   {
      Print("CloudBridge: API returned HTTP ", status, " response=", CharArrayToString(result));
      return false;
   }
   Print("CloudBridge: telemetry accepted. HTTP ", status);
   return true;
}

int OnInit()
{
   if(StringLen(ApiBaseUrl) < 10 || StringFind(ApiBaseUrl, "https://") != 0)
   {
      Print("CloudBridge: ApiBaseUrl must be an HTTPS URL.");
      return INIT_PARAMETERS_INCORRECT;
   }
   ema_fast_handle = iMA(_Symbol, DataTimeframe, 6, 0, MODE_EMA, PRICE_CLOSE);
   ema_slow_handle = iMA(_Symbol, DataTimeframe, 24, 0, MODE_EMA, PRICE_CLOSE);
   adx_handle = iADX(_Symbol, DataTimeframe, 14);
   if(ema_fast_handle == INVALID_HANDLE || ema_slow_handle == INVALID_HANDLE || adx_handle == INVALID_HANDLE)
      return INIT_FAILED;
   EventSetTimer(MathMax(HeartbeatSeconds, 2));
   Print("CloudBridge initialized in READ-ONLY mode for ", _Symbol);
   SendTelemetry();
   return INIT_SUCCEEDED;
}

void OnTimer()
{
   SendTelemetry();
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(ema_fast_handle != INVALID_HANDLE) IndicatorRelease(ema_fast_handle);
   if(ema_slow_handle != INVALID_HANDLE) IndicatorRelease(ema_slow_handle);
   if(adx_handle != INVALID_HANDLE) IndicatorRelease(adx_handle);
}
