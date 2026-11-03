// Typewriter
(function(){
  var roles=["Mechanical Engineering Student","CNC Machining Intern","Robotics & EV Enthusiast"];
  var el=document.getElementById('typed'); var ri=0, ci=0, del=false;
  var reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(reduce){ el.textContent=roles[0]; return; }
  function tick(){
    var word=roles[ri];
    el.textContent=word.slice(0,ci);
    if(!del){ ci++; if(ci>word.length){ del=true; return setTimeout(tick,1600);} }
    else{ ci--; if(ci===0){ del=false; ri=(ri+1)%roles.length; } }
    setTimeout(tick, del?38:78);
  }
  tick();
})();
// Scroll reveal
(function(){
  var io=new IntersectionObserver(function(es){ es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('visible'); io.unobserve(e.target);} }); },{threshold:.12});
  document.querySelectorAll('.reveal').forEach(function(n){ io.observe(n); });
})();
// Particle network
(function(){
  var c=document.getElementById('particles'), ctx=c.getContext('2d'), W,H,pts=[];
  var reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function resize(){ W=c.width=window.innerWidth; H=c.height=window.innerHeight;
    var n=Math.min(90, Math.floor(W*H/16000)); pts=[];
    for(var i=0;i<n;i++) pts.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*.45,vy:(Math.random()-.5)*.45});
  }
  function draw(){
    ctx.clearRect(0,0,W,H);
    for(var i=0;i<pts.length;i++){ var p=pts[i];
      p.x+=p.vx; p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1; if(p.y<0||p.y>H)p.vy*=-1;
      ctx.beginPath(); ctx.arc(p.x,p.y,2,0,Math.PI*2); ctx.fillStyle='#be123c'; ctx.fill();
      for(var j=i+1;j<pts.length;j++){ var q=pts[j], dx=p.x-q.x, dy=p.y-q.y, d=dx*dx+dy*dy;
        if(d<130*130){ ctx.beginPath(); ctx.moveTo(p.x,p.y); ctx.lineTo(q.x,q.y); ctx.strokeStyle='rgba(244,63,94,'+(0.35*(1-d/(130*130)))+')'; ctx.lineWidth=1; ctx.stroke(); } }
    }
    if(!reduce) requestAnimationFrame(draw);
  }
  window.addEventListener('resize',resize); resize(); draw();
})();
