import "./css/boot.scss";

// Main logged-in page.
// Login page (and all non-logged-in flow) is handled in login.js

import ReactDOM from 'react-dom';
import React from 'react';

import {BrowserRouter as Router, Route, Switch} from 'react-router-dom'

import Container from 'react-bootstrap/Container'
import FlashBox from './common/flashbox'

import {SignupManualCode} from './signup_wizard/create_account';

function SignupWizard() {
	return (
	<Router basename="/signup">
		<div style={{
			minWidth: "100vw",
			width: "100vw",
			minHeight: "100vh",
			height: "100vh",
			display: "flex",
			alignItems: "center"
		}}>
			<Container>
				<FlashBox />
				<div className="justify-content-center">
					<Switch>
						<Route path="/" exact>
							<SignupManualCode />
						</Route>
					</Switch>
				</div>
			</Container>
		</div>
	</Router>
	);
}

const mount = document.getElementById("mount");
ReactDOM.render(<SignupWizard />, mount);