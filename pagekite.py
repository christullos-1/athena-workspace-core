<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<!-- encoding: utf-8 -->
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1" />
  <meta name="HandheldFriendly" content="true" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />

  <title>Pagekite -
    
  The fast, reliable localhost tunneling solution

    
  </title>

  <link href="/static/skin/main.css" media="all" rel="stylesheet" type="text/css" />
  <!--[if (lt IE 9)&(!IEMobile) ]><link href="/static/skin/main-full.css" media="all" rel="stylesheet" type="text/css" /> <![endif]--><!--[if (gte IE 9)|!(IE)]><!-->
  <link href="/static/skin/main-full.css" media="all and (min-width: 720px) and (min-device-width: 720px)" rel="stylesheet" type="text/css" /><!--<![endif]-->
  <link rel="shortcut icon" href="/static/skin/i/fav.ico" />
  
  <script>
    (function(){
      window.PK = window.PK || {};
      // check if user is flagged as logged in.
      window.PK.loggedIn = /name=/.test(document.cookie);
      // make note of referrals.
      var match = window.location.search.match(/(?:\?|&)(referrer=[^&]*?)/);
      if (match)
      {
        var date = new Date();
        date.setTime( date.getTime() + (2 *24*60*60*1000) ); // referral code lasts for two days
        document.cookie = match[1] + '; expires='+ date.toUTCString() +'; path=/;';
      }
    })();
  </script>

  
  <style type='text/css'>
    
    a.page6 {color: #000; font-weight: bold; text-decoration: none;}
  </style>
  
  <script src="/static/skin/noflicker.js"></script>


  <link rel="alternate" type="application/rss+xml" title="RSS" href="/Blog?rss=1" />

  <style type='text/css'>
    #edit_button {position: absolute; right: 0;}
  </style>
  <base href="https://pagekite.net/">

</head>
<!--[if lt IE 9 ]><body class="msie"> <![endif]--><!--[if (gte IE 9)|!(IE)]><!-->
<body> <!--<![endif]--><div class="pgall">

  <div class="pghead"><a id='top' name='top'></a>
    <h1 class="brand">
      <a href="/" title="Pagekite - home">
        <img class="logo" src="/static/skin/i/pagekite-logo.png" alt="Pagekite" />
      </a>
      <span class="slogan">the fast, reliable localhost tunneling solution</span>
    </h1>

    <p class="stream skiplink"><a href='#pgnav'>Skip to navigation</a></p>
    <hr class="stream" />
  </div><!-- /.pghead -->

  
 
 <div class=pgmiddle2><div class="wrap"><div class="cols cols-2"><div class="col">
<p style='margin-top: 0.3em'>
 Fast, reliable, secure: make your <b>localhost</b> part of the Web.
</p><p>
Since 2010, PageKite has led the way in making local servers public. With relays on four continents, it works with any computer, any web server and any Internet connection.
</p><p>
 It's also 100% <a href='/wiki/OpenSource/'>Open Source</a>.
 <a href='/downloads/' style='float: right; margin-top: 30px;' class='bigbtn '>Download</a>
</p><br clear="both"></div>
<div class="col">
<div><div class=pgembed> <p style='display: inline-block; float: right; font-size: 0.9em;'> <a onClick='return tab("s3win");' href='/downloads/#s3win'>Win</a><span id='macLink1'> | <a onClick='return tab("s3mac");' href='/downloads/#s3mac'>Mac</a> </span><span id='macLink2' style='display: none;'> | <a onClick='return tab("s3oldmac");' href='/downloads/#s3mac'>Mac</a></span> | <a onClick='return tab("s3linux");' href='/downloads/#s3linux'>Linux</a> <!-- | <a onClick='return tab("s3and");' href='/downloads/#s3and'>Android</a> --> | <a href='/downloads/'>more ...</a> </p><div id='s3win' style='display: block; padding: 0; margin: 0;'><h3 id="h3wfp">Windows flight plan</h3> <ol> <li>Download and install <a href='https://www.python.org/downloads/windows/'>Python 3.x</a></li> <li><a href='https://pagekite.net/pk/pagekite.py'>Download <tt>pagekite.py</tt></a> to your Desktop</li> <li>Run the program!</li> </ol> <p>Answer a few quick questions and you'll be flying in no time.</p> </div> <div id='s3oldmac' style='display: none; padding: 0; margin: 0;'><h3 id="h3moxfp">Mac OS X flight plan</h3> <p>In the Terminal, run:</p> <ul><small><tt> $ curl -s https://pagekite.net/pk/pagekite.py >pagekite.py<br> $ python3 pagekite.py 80 <i>yourname</i>.pagekite.me </tt></small></ul> <p>Access <a>https://yourname.pagekite.me/</a> from anywhere!</p> </div> <div id='s3mac' style='display: none; padding: 0; margin: 0;'><h3 id="h3moql">Mac OS quick launch</h3> <p>In the Terminal, run:</p> <ul><small><tt> $ curl -O https://pagekite.net/pk/pagekite.py<br> $ python3 pagekite.py 80 <i>yourname</i>.pagekite.me </tt></small></ul> <p>Access <a>https://yourname.pagekite.me/</a> from anywhere!</p> </div> <div id=s3linux style='display: none; padding: 0; margin: 0;'><h3 id="h3lql">Linux quick launch</h3> <p>In a console, run:</p> <ul><small><tt> $ curl -O https://pagekite.net/pk/pagekite.py<br> $ python3 pagekite.py 80 <i>yourname</i>.pagekite.me </tt></small></ul> <p>Access <a>https://yourname.pagekite.me/</a> from anywhere!</p> </div> <div id=s3and style='display: none; padding: 0; margin: 0;'><h3 id="h3afp">Android flight plan</h3> <ul> <li>Install <a href='https://play.google.com/store/apps/details?id=net.pagekite.app'>PageKite for Android</a>.</li> <li>Install a web server or SSH server app.</li> </ul> <p>Access <a>https://yourname.pagekite.me/</a> from anywhere!</p> </div> <script language=javascript> function show(sid, how) {document.getElementById(sid).style.display = how || 'block';} function hide(hid) {document.getElementById(hid).style.display = 'none';} function tab(tid) {hide('s3win');hide('s3mac');hide('s3oldmac');hide('s3linux');hide('s3and');show(tid); return false;} </script> <script language='javascript'> if (navigator.appVersion.indexOf("Win") != -1) { tab("s3win"); } else if ((navigator.userAgent.indexOf("OS X 10.4") != -1) || (navigator.userAgent.indexOf("OS X 10.5") != -1)) { tab("s3oldmac"); show('macLink2', 'inline'); hide('macLink1'); } else if (navigator.appVersion.indexOf("Mac") != -1) { tab("s3mac"); } else if (navigator.appVersion.indexOf("DISABLED_Android") != -1) { tab("s3and"); } else if (navigator.appVersion.indexOf("X11") != -1) { tab("s3linux"); } else if (navigator.appVersion.indexOf("Linux") != -1) { tab("s3linux"); } </script> <ul class="tagitems"> </ul> </div> </div>
</div></div></div></div>
 
 <div class=pgmiddle>
  






  
   
  

  

  
    <div style="text-align: center;">
 <h2 id="h2wcidwp" style="white-space: nowrap; margin: 45px 0 10px 0;">What can I do with PageKite?</h2>
</div>

<div class="cols cols-3 usergroups">
 <div class="features box"><h4 id="h4hat">Hackers &amp; Tinkerers</h4>
   <ul>
     <li>Make any computer a server! A Raspberry Pi, a laptop, even old cell phones.</li>
     <li>Host at home: Wordpress, Nextcloud, Mailpile, Mastodon ... and all the rest.</li>
     <li>Simplify <a href='/wiki/Howto/SshOverPageKite/'>SSH access</a> to mobile or virtual machines.</li>
     <li><a href='http://pagekite.net/wiki/Floss/FreedomAndPrivacy/'>Protect your privacy</a>, take control of your data and logs.</li>
     <li>Make your sites public, but keep your home IP hidden.</li>
   </ul>
 </div>

 <div class="features box"><h4 id="h4ed">Embedded Developers</h4>
   <ul>
     <li>Name and access devices in the field, even over hostile 3rd party networks.</li>
     <li>Avoid botnets: with PageKite, the firewall stays closed and your devices are protected.</li>
     <li>Secure communications with wild-card relay certs or end-to-end TLS.</li>
     <li>Scale down with <a href="https://github.com/pagekite/libpagekite">libpagekite</a> (C) or <a href="https://github.com/pagekite/upagekite">upagekite</a> (micropython/ESP32).</li>
     <li>Scale up: our global relay network guarantees low latency and a good user experience.</li>
     <li>Out-source ops and improve uptime with <a href='/support/intro/features/'>our redundant infrastructure</a> - fully managed since 2010!</li>
     <li>Future-proof your business by building on Open Source and open standards.</li>
   </ul>
 </div>

 <div class="features box"><h4 id="h4wd">Web Developers</h4>
   <ul>
     <li>Skip deployment, let colleagues and clients test or remote-debug your work directly.</li>
     <li>Simplify testing on mobile devices and live networks.</li>
     <li>Interact with secure APIs and protect your work using our automatic TLS support.</li>
     <li>Run webhooks, API servers or <a href='/wiki/Howto/EasilyShareGitRepos/'>git repos</a>
          on your desktop, laptop, or in a VM.</li>
   </ul>
 </div>
</div>

<div style="border-top: 1px solid #e7e7e7; border-bottom: 2px solid #f7f7f7; padding: 18px 2000px; margin: 65px -2000px 40px -2000px; background: #f0f0f0;">
 <div class="cols cols-3 howitworks">
  <h2 id="h2hdiw">How does it work?</h2>
  <div class="col w-2_3">
   <img style="max-width: 96%;" src="/uploads/5ad7aef2-8711861_pk-ascii-ss2.png">
  </div>
  <div class="col">
     <p style="margin-top: 10px;">
       <b>Your servers run on your computers</b>
     </p><p>
       PageKite works with all HTTP and HTTPS servers, as well as SSH and few other TCP-based protocols.
     </p>
     <p>
       <br><b>pagekite.py connects to the cloud</b>
     </p><p>
       The pagekite.py (or libpagekite) tool automatically selects the closest working relay,
       minimizing latency and avoiding network outages.
     </p>
     <p>
       <br><b>pagekite.net relays your traffic</b>
     </p><p>
       Nobody ever needs to know your IP address, all traffic passes through our relays.
       For even more privacy, we support both end-to-end and wild-card TLS encryption.
     </p>
  </div>
 </div>
 <p style='text-align: center;'>
    See the <a href='/support/quickstart/'>quick-start guide</a>,
    <a href='/support/faq/'>FAQ</a> or
    <a href='/support/intro/features/'>feature list</a> for more details.
  </p>
</div>


<div class="cols cols-3">

<div class="qpricing col">
   <h3 id="h3p">Pricing</h3>
   <p><b>1 month free trial.</b></p>
   <p>Individuals can use it for <b>free</b> or <i>pay what you want</i>:
         we ask for a mere <b>$3&nbsp;USD/month</b>.</p>
   <p>Subscription, group and embedded plans for the pros from
         <b>$5.99&nbsp;USD/month</b>.</p>
   <p class="act"><a class="more" href="/pricing/">Pricing details</a></p>
 </div>

 <div class="qfeatures col">
   <h3 id="h3f">Features</h3>
   <p><b>PageKite lets HTTP &amp; SSH servers run on <i>any</i> device.</b></p>
   <ul>
     <li>Easy to use</li>
     <li>Reliable and fast</li>
     <li>Stable DNS names</li>
     <li>Unlimited sub-domains</li>
     <li>Use your own domains</li>
     <li>Automatic <b>https://</b> security</li>
     <li>Open Source, designed for security, privacy &amp; digital freedom.</li>
   </ul>
   <p class="act"><a class="more" href="/support/intro/features/">Details</a></p>
 </div>

 <div class="qblog col">
   <h3 id="h3b">Blog</h3>
   
<div><ul class="tagitems"> <li> <span class="date">Oct. 28, 2021, 4:30 p.m.</span> <a href="/2021-10-28/Updating_TLS_certs,_new_public_ports">Updating TLS certs, new public ports</a> </li> <li> <span class="date">Oct. 14, 2020, 2:29 p.m.</span> <a href="/2020-10-11/New_minor_PageKite_release">New PageKite release, fixes relay connection issues</a> </li> <li> <span class="date">July 7, 2020, 7:27 p.m.</span> <a href="/2020-07-07/New_Support_Chat">New Support Chat</a> </li> </ul></div>

   <p class="act"><a class="more" href="/Blog">Read more posts</a></p>
 </div>
</div>


    
  

  

   

   

   






  



 </div>


  <div class="pgnav" id="pgnav"><a name="pgnav"></a>
    <hr class="stream" />
    <div class="mainmenu">
      <h2>Pagekite.net - main pages:</h2>
      <ul>
        <li class="home current"><a href="/">Home</a></li>
        <li class=""><a href="/Blog">Blog</a></li>
        <li class=""><a href="/pricing/">Pricing</a></li>
        <li class=""><a href="/support/">Support</a></li>
        <li class=""><a href="/wiki/">Wiki</a></li>
        <li class="userinfo">
          <a class="btn account" href="https://pagekite.net/home/">My Account</a>
          <script>
            document.write( PK.loggedIn ?
                              '<a class="logout" href="https://pagekite.net/home/?logout=1&at='+ (new Date()).getTime() +'">Log out</a>':
                              '<a class="signup" href="https://pagekite.net/signup/">Sign up</a>'
              );
          </script><noscript><a class="logout" href="https://pagekite.net/home/?logout=1">Log out</a></noscript>
        </li>
      </ul>
    </div>

  </div><!-- /.pgnav -->


  <div class="pgfoot">
    <hr class="stream" />
    <div class="footer">
     
 


     <div class=pgembed>
 






  

  

  
         <div class="col">
        <h3 id="h3tbpe">The Beanstalks Project ehf.</h3>
        <ul>
          <li><a href="/company/">About Us</a></li>
          <li><a href="/company/iceland/">Iceland? Really?</a></li>
        </ul>
      </div>

      <div class="col">
        <h4 id="h4s">Service</h4>
        <ul>
          <li><a href="/support/intro/">Overview</a></li>
          <li><a href="/pricing/">Pricing</a></li>
          <li><a href="/support/faq/">FAQ</a></li>
          <li><a href="/wiki/HowTo/">How-To</a></li>
          <li><a href="/humans.txt">TOS &amp; Privacy</a></li>
          <li><a href="/support/data-processing-statement/">GDPR</a></li>
        </ul>
      </div>

      <div class="col">
        <h4 id="h4r">Resources</h4>
        <ul>
          <li><a href="/wiki/">Wiki</a></li>
          <li><a href="/Blog/">Blog</a></li>
          <li><a href="/support/chat/">Chat</a></li>
          <li><a class="ext" href="https://pagekite.wordpress.com/">Status</a></li>
        </ul>
      </div>

      <div class="col">
        <h4 id="h4os">Open Source</h4>
        <ul>
          <li><a href="/wiki/OpenSource/">FOSS Wiki</a></li>
          <li><a href="/wiki/Floss/Video/">Video: Introduction</a></li>
          <li><a href="/wiki/Floss/FreedomAndPrivacy/">Freedom &amp; Privacy</a></li>
          <li><a href="/wiki/Floss/License/">License</a></li>
        </ul>
        <p>Find us on:</p>
        <ul>
          <li><a class="ext" href="https://github.com/pagekite/">Github</a></li>
        </ul>
      </div>

      <div class="col">
        <h4 id="h4cu">Contact Us</h4>
        <ul>
         <li>
            <a title="Follow PageKite on Twitter" href="https://twitter.com/PageKite"><img src="/static/skin/i/tw-button.png" alt="Twitter"/></a>
            <a title="Subscribe to our blog" href="/Blog?rss=1"><img src="/static/skin/i/rss-button.png" alt="RSS"></a></li>
         </li>
          <li><a href="/support/chat/">Live Chat</a></li>
        </ul>
        <p>Email:</p>
        <ul>
          <li><a class=mailto href="mailto:info.w2011@pagekite.net">info<noscript>spam</noscript>@pagekite.net</a></li>
        </ul>
      </div>
    
  

  
   <ul class="tagitems">
 
</ul>

  



 
</div>

     <div class="adbuttons">
      <a id="rannis"
         title="Our work was supported by the Icelandic Technology Development Fund."
         href="https://en.rannis.is/funding/research/technology-development-fund/"
       ><img src="/static/skin/i/rannis-tdfund.png"></a>
     </div>
    </div>
  </div><!-- /.pgfoot -->
  

</div>

</body></html>
