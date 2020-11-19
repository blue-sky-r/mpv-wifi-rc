#!/bin/bash

# version tag
#
VER="2020.11.17"

# debug output to the caller (will show as pop-up alert)
#
DBG=

# log to logger (empty for no logging)
#
LOG='tv.cgi'

# content-type
#
echo "Content-Type: text/plain"; echo

# debug or logger output
#
function msg()
{
    [   $DBG ] && echo -e "DBG: $1" && echo
    [ ! $DBG ] && [ -n "$LOG" ] && logger -t "$LOG" "$@"
}

msg "QUERY_STRING:${QUERY_STRING}"

# shutdown (add to sudoers: iptv    ALL = (ALL) NOPASSWD: /sbin/poweroff)
#
shutdown="sudo /sbin/poweroff"

# directories
#
dirbin="bin"
dirm3u8="/home/iptv/m3u8"
#dirm3u8="../../m3u8"

# playlists
#
plistraw="tv.m3u8.raw"
plistenv="tv-env.m3u8"

# mpv control socket
#
mpvsocket="socat - /tmp/mpvsocket"

# json
#
function json
{
    local key=$1
    python -c "import sys, json; print json.load(sys.stdin).get($key)"
}

# refresh playlist with fresh auth tokens/urls
#
function refresh_tokens
{
    local force=$1

    $dirbin/envsubst-playlist.sh "$dirm3u8/$plistraw" "$dirm3u8/$plistenv" "$force"
}

# send to mpv
#
function mpv_send
{
    local str

    # build str=par1 "par2" ... "parX"
    #
    for s in "$@"
    {
        # the first string without quotes
        [ -z "$str" ] && str=$s && continue
        # add only non empty strings
        [ -n "$s" ] && str="$str \"$s\""
    }

    # optional log
    msg "mpv_send: $str"
    #
    echo "$str" | $mpvsocket
}

# command to mpv
#
function mpv_cmd
{
    local str
    local sep

    # build str="par1","par2"..."parX"
    #
    for s in "$@"
    {
        str="${str}${sep}\"${s}\""
        sep=', '
    }

    # optional log
    msg "mpv_cmd: [ $str ]"
    #
    echo "{ \"command\": [ $str ] }" | $mpvsocket
}

# display OSD
#
function osd
{
    # escape double-quotes
    local txt=${1//\"/\\\"}
    local time=$2

    # optional log
    msg "osd: $txt, time:$time"
    #
    mpv_send "show-text" "$txt" "$time"
}

# split by &
#
for keyval in ${QUERY_STRING//&/ }
{
	# split key=val
	#
	key=${keyval%=*}
	val=${keyval#*=}
	
	# + -> space
	val=${val//+/ }
	# %xy -> char
	val=$( printf '%b' "${val//%/\\x}" )

	msg "keyval($keyval) => key($key) val($val)"

    # use the first key as command CMD
    #
	[ -z "$CMD" ] && CMD=$key

    # define parametric variable assignment
    #
    [ -n "$val" ] && declare -r ${key//-/_}="$val" && msg "declared variable ${key//-/_} = $val"
}

# execute command CMD
#
case $CMD in

    # channel=cnn
    channel)
                # refresh auth tokens only for specific channels
                #if [[ $channel =~ STV1|STV2|STV3|STV4|DAJTO|DOMA|MARKÍZA ]]
                if [[ $channel =~ Dajto|Doma|Markíza ]]
                then
                    # loadlist <playlist> [replace|append] - not required ?
                    refresh_tokens && r=$( mpv_cmd "loadlist" "$dirm3u8/$plistenv" "replace" )
                fi
                r=$( mpv_send "script-message-to channel_by_name channel" "$channel" )
                ;;

    # survey-range-playlist=playlist & start=name & end=name [& osd=message]
    survey-range-playlist)
                # survey_range_playlist "chan 1" "chan 10" ["playlist.m3u8" ["OSD message"]]
                r=$( mpv_send "script-message-to channel_survey survey_range_playlist" "$start" "$end" "$survey_range_playlist" "$osd" )
                ;;

    # survey-list-playlist=playlist & list=list [ & osd=message]
    survey-list-playlist)
                # survey_list_playlist "chan 1,chan 10" ["playlist.m3u8" ["OSD message"]]
                r=$( mpv_send "script-message-to channel_survey survey_list_playlist" "$list" "$survey_list_playlist" "$osd" )
                ;;

    # show-text=test msg
    show-text)	r=$( osd "$show_text" )
                ;;

    # show-text=test msg with ass control codes
    show-text-ass-cc)
                # get control code for disabling escaping ass sequences
    	        esc0=$( mpv_cmd "get_property" "osd-ass-cc/0" | awk -F'"' '/data/ {printf "%s",$4}' )
    	        #esc0='\xfd'
                # execute show-text and escape double-quotes in text
                #r=$( mpv_send "show-text" "${esc0}${show_text_ass_cc//\"/\\\"}" "$time" )
                r=$( osd "${esc0}${show_text_ass_cc}" "$time" )
                ;;

    # clock
    clock)		r=$( mpv_send "keypress h" )
                ;;

    # email
    email)		r=$( mpv_send "keypress e" )
                ;;

    # weather
    weather)	r=$( mpv_send "keypress w" )
                ;;

    # info
    info)		r=$( mpv_send "keypress i" )
                ;;

    # get active channel title/name (json)
    get-title)	json=$( mpv_cmd "get_property" "media-title" )
                # output json: {"data":"Wau,,0","error":"success"}
                echo "$json"
                ;;

    # direct command
    # '{ "command": ["set", "pause", "yes"] }'
    # '{ "command": ["seek", "-10"] }'
    cmd)        r=$( mpv_cmd ${cmd} )
                ;;

    # get program
    get-epg)
                json=$( ./epg.py -title "${channel}" -offset ${offset} -bar ${barsize} -epg )
                # output
                echo "$json"
                ;;

    # get program list
    get-epg-list)
                # get epg
                json=$( ./epg.py -title "${channel}" -offset ${offset} -epg-list ${get_epg_list} )
                # output
                echo "$json"
                ;;

    # mpv --list-properties
    # echo '{ "command": ["get_property", "video-out-params"] }'  | socat - /tmp/mpvsocket
    # {"data":{"pixelformat":"yuv420p","average-bpp":12,"plane-depth":8,"w":640,"h":360,"dw":640,"dh":360,"aspect":1.777778,
    # "par":1.000000,"colormatrix":"bt.601","colorlevels":"limited","primaries":"bt.709","gamma":"bt.1886","sig-peak":1.000000,
    # "light":"display","chroma-location":"mpeg2/4/h264","stereo-in":"mono","rotate":0},"error":"success"}
    # get active channel title/name (json)
    get-property)
                json=$( mpv_cmd "get_property" "${get_property}" )
                # output json
                echo "$json"
                ;;

    # refresh auth tokens/utls in playlist
    playlist)
                case $playlist in

                reload)
                    osd "obnovenie ..."
                    refresh_tokens "force"
                    # loadlist <playlist> [replace|append] - not required ?
                    #r=$( echo '{ "command": ["loadlist", "'$dirm3u8/$plistenv'", "replace"] }' | $mpvsocket )
                    r=$( mpv_cmd "loadlist" "$dirm3u8/$plistenv" "replace" )
                    ;;

                playlist-prev | playlist-next)
                    #r=$( echo '{ "command": ["'${playlist}'"] }' | $mpvsocket )
                    r=$( mpv_cmd "${playlist}" )
                    ;;

                esc)
                    osd "reštartovanie ..."
                    # save current channel
                    property='playlist-pos-1'
                    # {"data":1,"request_id":0,"error":"success"}
                    pos1=$( mpv_cmd "get_property" "${property}" | awk -F:\|, '{print $2}' )
                    # no response as mpv will quit
                    mpv_send "keypress ESC"
                    # wait for mpv restart
                    sleep 2.8
                    # restore saved channel
                    r=$( mpv_cmd "set_property" "${property}" "${pos1}" )
                    ;;

                meteogram)
                    r=$( export DISPLAY=:0; $dirbin/display-meteogram.sh 2>&1 )
                    ;;

                shutdown)
                    # osd info
                    osd "vypínanie ..."
                    # shutdown
#                    r=$( export DISPLAY=:0; $shutdown 2>&1 )
                    mpv_send "keypress CRTL+r"
                    ;;

                esac
                ;;

    # youtube list channel videos
    yt-list)
                json=$( youtube-dl -j --restrict-filenames --socket-timeout 5 \
                --playlist-start $idxfrom --playlist-end $idxto --flat-playlist \
                http://www.youtube.com/${channel} \
                | sed -e 's/\[Cel\\u00fd Film v \\u010ce\\u0161tin\\u011b\]//g' -e 's/\[\?\\u010cesk\\u00fd Dabing\]\?//g' \
                | tr "\n" "," | sed -e 's/,$//' )
                # output json
                echo "[ $json ]"
                ;;

    yt-watch)
                url=; [[ $yt_watch =~ ^[A-Za-z0-9_-]+$ ]] && url="ytdl://www.youtube.com/watch?v="
                r=$( mpv_cmd "loadfile" "${url}${yt_watch}" "replace" )
                # autoplay
                sleep 8
                r=$( mpv_cmd "set" "pause" "no" )
                ;;

    *)		    echo "unrecognized command:$CMD - query:$QUERY_STRING"
                ;;
esac

# result output from mpv socket
#
msg "result: [$r]"

