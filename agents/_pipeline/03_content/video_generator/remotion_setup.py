"""
AUROS AI — Remotion Video Ad Generator
Programmatic video ad creation using Remotion (React-based video framework).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from agents.shared.config import PROJECT_ROOT, PORTFOLIO_DIR


PACKAGE_JSON = '{"name":"auros-video-ads","version":"1.0.0","private":true,"scripts":{"studio":"npx remotion studio","render":"npx remotion render"},"dependencies":{"@remotion/cli":"^4.0.0","react":"^18.2.0","react-dom":"^18.2.0","remotion":"^4.0.0"},"devDependencies":{"typescript":"^5.0.0","@types/react":"^18.2.0"}'


def check_remotion_installed():
    try:
        r = subprocess.run(["node","--version"], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_exhibition_colors(exhibition):
    name = exhibition.lower()
    if "harry potter" in name:
        return {"brand": "#5C1A1A", "accent": "#C9A84C"}
    elif "titanic" in name:
        return {"brand": "#1F3A52", "accent": "#D4AF37"}
    elif "van gogh" in name:
        return {"brand": "#1a2e0a", "accent": "#E8C96A"}
    elif "dinosaur" in name or "ice" in name:
        return {"brand": "#0a1e2e", "accent": "#93c5fd"}
    return {"brand": "#0B0F1A", "accent": "#C9A84C"}


def _ad_template_15s(brand, accent):
    return '''import {AbsoluteFill,useCurrentFrame,interpolate,spring,useVideoConfig,Sequence} from "remotion";
import React from "react";

interface Props {exhibitionName:string;headline:string;cta:string;}

export const ExhibitionAd15s:React.FC<Props> = ({exhibitionName,headline,cta}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t1 = interpolate(frame,[0,20],[0,1],{extrapolateRight:"clamp"});
  const t1y = interpolate(frame,[0,20],[60,0],{extrapolateRight:"clamp"});
  const t2 = interpolate(frame,[60,90],[0,1],{extrapolateRight:"clamp"});
  const ctaS = spring({frame:frame-300,fps,config:{damping:12}});
  const ctaO = interpolate(frame,[300,330],[0,1],{extrapolateRight:"clamp"});

  return (
    <AbsoluteFill style={{background:"linear-gradient(180deg,BRAND_COLOR 0%,#000 100%)"}}>
      <Sequence from={0} durationInFrames={450}>
        <div style={{position:"absolute",top:"15%",width:"100%",textAlign:"center",opacity:t1,transform:`translateY(${t1y}px)`}}>
          <div style={{fontFamily:"Georgia,serif",fontSize:42,fontWeight:900,color:"ACCENT_COLOR",letterSpacing:4,textTransform:"uppercase"}}}>{exhibitionName}</div>
        </div>
      </Sequence>
      <Sequence from={60} durationInFrames={390}>
        <div style={{position:"absolute",top:"35%",width:"100%",padding:"0 60px",textAlign:"center",opacity:t2}}>
          <div style={{fontFamily:"Georgia,serif",fontSize:64,fontWeight:900,color:"#FAFAF8",lineHeight:1.15}}}>{headline}</div>
        </div>
      </Sequence>
      <Sequence from={300} durationInFrames={150}>
        <div style={{position:"absolute",bottom:"12%",width:"100%",textAlign:"center",opacity:ctaO,transform:`scale(${ctaS})`}}>
          <div style={{display:"inline-block",padding:"20px 48px",background:"ACCENT_COLOR",borderRadius:12,fontFamily:"Inter,sans-serif",fontSize:28,fontWeight:800,color:"BRAND_COLOR",letterSpacing:2,textTransform:"uppercase"}}}>{cta}</div>
        </div>
      </Sequence>
    </AbsoluteFill>
  );
};'''.replace('BRAND_COLOR', brand).replace('ACCENT_COLOR', accent)


def _ad_template_30s(brand, accent):
    return '''import {AbsoluteFill,useCurrentFrame,interpolate,spring,useVideoConfig,Sequence} from "remotion";
import React from "react";

interface Props {exhibitionName:string;headline:string;cta:string;}

export const ExhibitionAd30s:React.FC<Props> = ({exhibitionName,headline,cta}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p1 = interpolate(frame,[0,30],[0,1],{extrapolateRight:"clamp"});
  const p2 = interpolate(frame,[150,180],[0,1],{extrapolateRight:"clamp"});
  const ctaS = spring({frame:frame-750,fps,config:{damping:12}});

  return (
    <AbsoluteFill style={{background:"linear-gradient(135deg,BRAND_COLOR 0%,#0a0a0a 50%,BRAND_COLOR 100%)"}}>
      <Sequence from={0} durationInFrames={150}>
        <div style={{position:"absolute",top:"40%",width:"100%",textAlign:"center",opacity:p1}}>
          <div style={{fontFamily:"Georgia,serif",fontSize:56,fontWeight:900,color:"#FAFAF8",padding:"0 80px"}}}>Everyone is talking about this...</div>
        </div>
      </Sequence>
      <Sequence from={150} durationInFrames={300}>
        <div style={{position:"absolute",top:"10%",width:"100%",textAlign:"center",opacity:p2}}>
          <div style={{fontFamily:"Georgia,serif",fontSize:36,color:"ACCENT_COLOR",letterSpacing:4,textTransform:"uppercase",marginBottom:24}}}>{exhibitionName}</div>
          <div style={{fontFamily:"Georgia,serif",fontSize:72,fontWeight:900,color:"#FAFAF8",padding:"0 100px",lineHeight:1.1}}}>{headline}</div>
        </div>
      </Sequence>
      <Sequence from={450} durationInFrames={300}>
        <div style={{position:"absolute",top:"35%",width:"100%",textAlign:"center"}}>
          <div style={{fontFamily:"Inter,sans-serif",fontSize:48,fontWeight:900,color:"ACCENT_COLOR"}}}>500,000+ visitors</div>
          <div style={{fontFamily:"Inter,sans-serif",fontSize:28,color:"#9CA3AF",marginTop:12}}}>Rated 4.9/5 across 15 cities worldwide</div>
        </div>
      </Sequence>
      <Sequence from={750} durationInFrames={150}>
        <div style={{position:"absolute",bottom:"15%",width:"100%",textAlign:"center",transform:`scale(${ctaS})`}}>
          <div style={{display:"inline-block",padding:"20px 56px",background:"ACCENT_COLOR",borderRadius:12,fontFamily:"Inter,sans-serif",fontSize:32,fontWeight:800,color:"BRAND_COLOR",letterSpacing:2}}}>{cta}</div>
        </div>
      </Sequence>
    </AbsoluteFill>
  );
};'''.replace('BRAND_COLOR', brand).replace('ACCENT_COLOR', accent)


def _ad_template_60s(brand, accent):
    return '''import {AbsoluteFill,useCurrentFrame,interpolate,spring,useVideoConfig,Sequence} from "remotion";
import React from "react";

interface Props {exhibitionName:string;headline:string;cta:string;}

export const ExhibitionAd60s:React.FC<Props> = ({exhibitionName,headline,cta}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const f1 = interpolate(frame,[0,30],[0,1],{extrapolateRight:"clamp"});
  const f2 = interpolate(frame,[300,330],[0,1],{extrapolateRight:"clamp"});
  const f3 = interpolate(frame,[750,780],[0,1],{extrapolateRight:"clamp"});
  const f4 = interpolate(frame,[1200,1230],[0,1],{extrapolateRight:"clamp"});
  const ctaS = spring({frame:frame-1500,fps,config:{damping:12}});

  return (
    <AbsoluteFill style={{background:"#000"}}>
      <Sequence from={0} durationInFrames={300}>
        <AbsoluteFill style={{background:"linear-gradient(180deg,BRAND_COLOR 0%,#000 100%)",opacity:f1}}>
          <div style={{position:"absolute",top:"40%",width:"100%",textAlign:"center"}}>
            <div style={{fontFamily:"Georgia,serif",fontSize:32,color:"#6B7280",letterSpacing:6,textTransform:"uppercase"}}}>Imagine stepping into</div>
          </div>
        </AbsoluteFill>
      </Sequence>
      <Sequence from={300} durationInFrames={450}>
        <AbsoluteFill style={{background:"radial-gradient(ellipse at 50% 50%,BRAND_COLOR33 0%,#000 70%)",opacity:f2}}>
          <div style={{position:"absolute",top:"25%",width:"100%",textAlign:"center"}}>
            <div style={{fontFamily:"Georgia,serif",fontSize:80,fontWeight:900,color:"ACCENT_COLOR",letterSpacing:-2,marginBottom:24}}}>{exhibitionName}</div>
            <div style={{fontFamily:"Georgia,serif",fontSize:40,color:"#FAFAF8",padding:"0 120px",lineHeight:1.3,fontStyle:"italic"}}}>{headline}</div>
          </div>
        </AbsoluteFill>
      </Sequence>
      <Sequence from={750} durationInFrames={450}>
        <AbsoluteFill style={{background:"#000",opacity:f3}}>
          <div style={{position:"absolute",top:"20%",width:"100%",textAlign:"center"}}>
            <div style={{fontFamily:"Inter,sans-serif",fontSize:96,fontWeight:900,color:"ACCENT_COLOR"}}}>500,000+</div>
            <div style={{fontFamily:"Inter,sans-serif",fontSize:28,color:"#9CA3AF",marginTop:8}}}>visitors across 15 cities</div>
            <div style={{marginTop:60,fontFamily:"Inter,sans-serif",fontSize:56,fontWeight:900,color:"#FAFAF8"}}}>4.9/5 rating</div>
          </div>
        </AbsoluteFill>
      </Sequence>
      <Sequence from={1200} durationInFrames={600}>
        <AbsoluteFill style={{background:"linear-gradient(180deg,#000 0%,BRAND_COLOR 100%)",opacity:f4}}>
          <div style={{position:"absolute",top:"30%",width:"100%",textAlign:"center"}}>
            <div style={{fontFamily:"Georgia,serif",fontSize:48,fontWeight:900,color:"#FAFAF8",marginBottom:16}}}>Limited dates remaining</div>
          </div>
          <div style={{position:"absolute",bottom:"15%",width:"100%",textAlign:"center",transform:`scale(${ctaS})`}}>
            <div style={{display:"inline-block",padding:"24px 64px",background:"ACCENT_COLOR",borderRadius:16,fontFamily:"Inter,sans-serif",fontSize:36,fontWeight:800,color:"BRAND_COLOR",letterSpacing:2,textTransform:"uppercase"}}}>{cta}</div>
          </div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};'''.replace('BRAND_COLOR', brand).replace('ACCENT_COLOR', accent)


def _root_component(exhibition, headline, cta, brand, accent):
    return '''import {Composition} from "remotion";
import {ExhibitionAd15s} from "./ExhibitionAd15s";
import {ExhibitionAd30s} from "./ExhibitionAd30s";
import {ExhibitionAd60s} from "./ExhibitionAd60s";

export const RemotionRoot:React.FC = () => {
  return (
    <>
      <Composition id="ExhibitionAd15s" component={ExhibitionAd15s} durationInFrames={450} fps={30} width={1080} height={1920}
        defaultProps={{exhibitionName:"{exhibition}",headline:"{headline}",cta:"{cta}"}} />
      <Composition id="ExhibitionAd30s" component={ExhibitionAd30s} durationInFrames={900} fps={30} width={1920} height={1080}
        defaultProps={{exhibitionName:"{exhibition}",headline:"{headline}",cta:"{cta}"}} />
      <Composition id="ExhibitionAd60s" component={ExhibitionAd60s} durationInFrames={1800} fps={30} width={1920} height={1080}
        defaultProps={{exhibitionName:"{exhibition}",headline:"{headline}",cta:"{cta}"}} />
    </>
  );
};'''.replace('BRAND_COLOR', brand).replace('ACCENT_COLOR', accent)


def generate_video_project(script_data, exhibition, output_dir=None):
    if output_dir is None:
        output_dir = str(PORTFOLIO_DIR / "client_the_imagine_team" / "video_projects")

    safe_name = exhibition.lower().replace(" ", "_").replace(":", "")
    project_dir = Path(output_dir) / safe_name
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    colors = _get_exhibition_colors(exhibition)
    scripts = script_data.get("scripts", [])
    headline = scripts[0].get("title", exhibition) if scripts else exhibition
    cta_raw = scripts[0].get("cta", "Get Tickets Now") if scripts else "Get Tickets Now"
    cta = cta_raw.split("\u2192")[0].strip() if "\u2192" in cta_raw else cta_raw

    (project_dir / "package.json").write_text(PACKAGE_JSON)
    (src_dir / "index.ts").write_text('import {registerRoot} from "remotion";\nimport {RemotionRoot} from "./Root";\nregisterRoot(RemotionRoot);\n')
    (src_dir / "Root.tsx").write_text(_root_component(exhibition, headline, cta, colors["brand"], colors["accent"]))
    (src_dir / "ExhibitionAd15s.tsx").write_text(_ad_template_15s(colors["brand"], colors["accent"]))
    (src_dir / "ExhibitionAd30s.tsx").write_text(_ad_template_30s(colors["brand"], colors["accent"]))
    (src_dir / "ExhibitionAd60s.tsx").write_text(_ad_template_60s(colors["brand"], colors["accent"]))

    print(f"[AUROS] Remotion project generated at {project_dir}")
    return str(project_dir)


def render_video(project_dir, composition, output_path):
    try:
        r = subprocess.run(["npx","remotion","render",composition,output_path],
            cwd=project_dir, capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            print(f"[AUROS] Video rendered: {output_path}")
            return output_path
        print(f"[AUROS] Render failed: {r.stderr[:500]}")
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[AUROS] Cannot render: {e}")
        return None


def render_all_formats(project_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    rendered = []
    for comp in ["ExhibitionAd15s", "ExhibitionAd30s", "ExhibitionAd60s"]:
        out = os.path.join(output_dir, f"{comp}.mp4")
        r = render_video(project_dir, comp, out)
        if r:
            rendered.append(r)
    return rendered


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AUROS Remotion Video Generator")
    parser.add_argument("--exhibition", required=True)
    parser.add_argument("--scripts", help="Path to video scripts JSON")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()

    script_data = {}
    if args.scripts:
        with open(args.scripts) as f:
            script_data = json.load(f)

    if not check_remotion_installed():
        print("[AUROS] Node.js not found.")
        exit(1)

    path = generate_video_project(script_data, args.exhibition, args.output)
    print(f"\n[AUROS] Project ready: {path}")
    print(f"[AUROS] Preview: cd '{path}' && npm install && npm run studio")

    if args.render:
        from agents.video_generator.remotion_setup import install_dependencies
        install_dependencies(path)
        render_all_formats(path, os.path.join(path, "output"))
