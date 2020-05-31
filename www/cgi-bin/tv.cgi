#!/bin/bash

# version tag
#
VER="2020.05.30"

# debug output to the caller (will show as pop-up alert)
#
DBG=

echo "Content-Type: text/plain"; echo

[ $DBG ] && (echo "DBG: QUERY_STRING:${QUERY_STRING}"; echo)

# shutdown (add to sudoers: iptv ALL=NOPASSWD:/sbin/poweroff)
#
shutdown="sudo /sbin/poweroff"
# iptv    localhost = NOPASSWD: /bin/systemctl poweroff
#shutdown="sudo /bin/systemctl --no-wall poweroff"

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

	[ $DBG ] && echo "keyval($keyval) => key($key) val($val)"

    # use the first key as command CMD
    #
	[ -z "$CMD" ] && CMD=$key

    # define parametric variable assignment
    #
    [ -n "$val" ] && declare -r ${key//-/_}="$val" && [ $DBG ] && echo "declared variable ${key//-/_} = $val"
}

# execute command CMD
#
case $CMD in

    # channel=cnn
    channel)
                # refresh auth tokens only for specific channels
                #if [[ $channel =~ STV1|STV2|STV3|STV4|DAJTO|DOMA|MARKÍZA ]]
                if [[ $channel =~ DAJTO|DOMA|MARKÍZA ]]
                then
                    # loadlist <playlist> [replace|append] - not required ?
                    refresh_tokens && \
                    r=$( echo '{ "command": ["loadlist", "'$dirm3u8/$plistenv'", "replace"] }' | $mpvsocket )
                fi
                r=$( echo "script-message-to channel_by_name channel \"$channel\"" | $mpvsocket )
                ;;

    # survey-range-playlist=playlist & start=name & end=name [& osd=message]
    survey-range-playlist)
                # survey_range_playlist "chan 1" "chan 10" ["playlist.m3u8" ["OSD message"]]
                r=$( echo "script-message-to channel_survey survey_range_playlist \
                    \"${start}\" \"${end}\" \"${survey_range_playlist}\" \"${osd}\" " \
                    | $mpvsocket )
                ;;

    # survey-list-playlist=playlist & list=list [ & osd=message]
    survey-list-playlist)
                # survey_list_playlist "chan 1,chan 10" ["playlist.m3u8" ["OSD message"]]
                r=$( echo "script-message-to channel_survey survey_list_playlist \
                    \"${list}\" \"${survey_list_playlist}\" \"${osd}\" " \
                    | $mpvsocket )
                ;;

    # show-text=test msg
    show-text)	r=$( echo "show-text \"${show_text}\"" | $mpvsocket )
                ;;

    # show-text=test msg with ass control codes
    show-text-ass-cc)
                # get control code for disabling escaping ass sequences
    	        esc0=$( echo '{ "command": ["get_property", "osd-ass-cc/0"] }' | $mpvsocket | awk -F'"' '/data/ {printf "%s",$4}' )
    	        #esc0='\xfd'
                # execute show-text and escape double-quotes in text
                r=$( echo "show-text \"${esc0}${show_text_ass_cc//\"/\\\"}\" ${time}"| $mpvsocket )
                #r=$( echo "{ \"command\": [\"show-text\", \"${esc0}${show_text_ass_cc//\"/\\\"}\", ${time}] }" | socat - /tmp/mpvsocket )
                ;;

    # clock
    clock)		r=$( echo "keypress h" | $mpvsocket )
                ;;

    # email
    email)		r=$( echo "keypress e" | $mpvsocket )
                ;;

    # weather
    weather)	r=$( echo "keypress w" | $mpvsocket )
                ;;

    # info
    info)		r=$( echo "keypress i" | $mpvsocket )
                ;;

    # get active channel title/name (json)
    get-title)	json=$( echo '{ "command": ["get_property", "media-title"] }' | $mpvsocket )
                # output json: {"data":"Wau,,0","error":"success"}
                echo "$json"
                ;;

    # direct command
    # '{ "command": ["set", "pause", "yes"] }'
    # '{ "command": ["seek", "-10"] }'
    cmd)        r=$( echo '{ "command": ["'${cmd// /\",\"}'"] }' | $mpvsocket )
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
                json=$( echo '{ "command": ["get_property", "'${get_property}'"] }' | $mpvsocket )
                # output json
                echo "$json"
                ;;

    # refresh auth tokens/utls in playlist
    playlist)
                case $playlist in

                reload)
                    r=$( echo "show-text \"obnovenie ...\"" | $mpvsocket )
                    refresh_tokens "force"
                    # loadlist <playlist> [replace|append] - not required ?
                    r=$( echo '{ "command": ["loadlist", "'$dirm3u8/$plistenv'", "replace"] }' | $mpvsocket )
                    ;;

                playlist-prev | playlist-next)
                    r=$( echo '{ "command": ["'${playlist}'"] }' | $mpvsocket )
                    ;;

                esc)
                    # save current channel
                    property='playlist-pos-1'
                    # {"data":1,"request_id":0,"error":"success"}
                    pos1=$( echo '{ "command": ["get_property", "'${property}'"] }' | $mpvsocket | awk -F:\|, '{print $2}')
                    # no response as mpv will quit
                    echo "keypress ESC" | $mpvsocket
                    # wait for mpv restart
                    sleep 2.8
                    # restore saved channel
                    echo '{ "command": ["set_property", "'${property}'", '${pos1}'] }' | $mpvsocket
                    ;;

                shutdown)
                    # osd info
                    r=$( echo "show-text \"vypínanie ...\"" | $mpvsocket )
                    # shutdown
                    r=$( $shutdown )
                    ;;

                esac
                ;;

    # youtube list channel videos
    yt-list)
                json=$( youtube-dl -j --restrict-filenames --socket-timeout 5 \
                --playlist-start $idxfrom --playlist-end $idxto --flat-playlist \
                http://www.youtube.com/channel/${channel}/videos | tr "\n" "," | sed -e 's/,$//' )
                # output json
                echo "[ $json ]"
                ;;

    yt-watch)
                url="ytdl://www.youtube.com/watch?v=$yt_watch"
                r=$( echo '{ "command": ["loadfile", "'${url}'", "replace"] }' | $mpvsocket )
                ;;

    *)		    echo "unrecognized command:$CMD - query:$QUERY_STRING"
                ;;
esac

# result output from mpv socket
#
[ $DBG ] && echo $r

