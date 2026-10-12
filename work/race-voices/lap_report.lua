local lap = tonumber(Arguments[1])
local logPath = (REPORT_LOG_ROOT or (os.getenv('USERPROFILE') .. '/Documents/Simulator Controller/Logs')) .. '/Basic Lap Report.log'
local log = io.open(logPath, 'a')
if log then
    log:write(os.date('%Y-%m-%d %H:%M:%S'), ' lap=', tostring(lap),
        ' time=', tostring(Rules.GetValue('Lap.' .. tostring(lap) .. '.Time', 0)), '\n')
    log:close()
end
if not lap or lap < 1 then return true end
if tonumber(Rules.GetValue('BasicReport.LastLap', 0)) >= lap then return true end
local time = tonumber(Rules.GetValue('Lap.' .. lap .. '.Time', 0))
if not time or time <= 0 then return true end
local valid = Rules.GetValue('Lap.' .. lap .. '.Valid', true)
valid = valid ~= false and valid ~= 'false' and valid ~= 0
local seconds = time / 1000
local minutes = math.floor(seconds / 60)
local message = string.format('本圈%d分%.1f秒。', minutes, seconds - minutes * 60)
local best = tonumber(Rules.GetValue('BasicReport.Best', 0))
if not valid then
    message = message .. '无效圈。'
elseif best and best > 0 then
    local delta = (time - best) / 1000
    if delta < -0.05 then
        message = message .. string.format('刷新最快圈，快%.1f秒。', -delta)
    elseif delta > 0.05 then
        message = message .. string.format('比最快圈慢%.1f秒。', delta)
    end
end
if valid and (not best or best == 0 or time < best) then
    Rules.SetValue('BasicReport.Best', time)
end
Rules.SetValue('BasicReport.LastLap', lap)
Assistant.Speak(message)
return true
