import {flatCurve} from './volume-curve.mjs';
export function trackState(track){return {instrument:track.instrument,mix:{gain:track.gain,pan:track.pan,mute:Boolean(track.mute),solo:Boolean(track.solo),curve:structuredClone(track.curve||flatCurve())},tone:structuredClone(track.tone||{brightness:.5,attack:.5,release:.5,drive:0,space:0})};}
